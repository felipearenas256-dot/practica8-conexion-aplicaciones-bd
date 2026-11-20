"""
ACTIVIDAD 5 – Proyecto integrador: página web de gestión académica (Flask).

  - MySQL  -> datos transaccionales: estudiantes, cursos, matrículas, usuarios,
              auditoría (SP, funciones y triggers de la Práctica 5).
  - MongoDB -> datos no estructurados: perfiles, logs de actividad y preferencias.
  - Autenticación con contraseñas hasheadas (tabla Usuario), bloqueo por intentos
    fallidos (contados en MongoDB) y protección CSRF en todos los formularios.
  - Todas las consultas parametrizadas (a través de dao.py).

Ejecutar:  python app.py   y abrir http://127.0.0.1:5000
Usuarios de prueba:  admin / Admin2026*   ·   lgomez / Laura2026*
"""
import csv
import io
import os
import secrets
from datetime import date
from functools import wraps

import mysql.connector
from flask import (
    Flask, Response, abort, flash, redirect, render_template, request, session, url_for,
)
from markupsafe import Markup

from dao import (
    CursoDAO, EstudianteDAO, LogDAO, MatriculaDAO, PerfilDAO, PreferenciaDAO, UsuarioDAO, huella_datos,
    resumen_bases,
)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.urandom(24)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
app.json.ensure_ascii = False  # el JSON mostrado conserva las tildes (Gómez, no Gómez)

MAX_INTENTOS = 5        # intentos fallidos permitidos...
MINUTOS_BLOQUEO = 10    # ...en esta ventana de tiempo


def log(accion, detalle=None):
    """Registra la acción en MongoDB; si Mongo no responde, la web sigue funcionando."""
    try:
        LogDAO.registrar(session.get("usuario", "anónimo"), accion, detalle)
    except Exception as err:
        app.logger.warning("No se pudo guardar el log en MongoDB: %s", err)


def login_requerido(rol=None):
    """Decorador: exige sesión iniciada (y opcionalmente un rol)."""
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if "usuario" not in session:
                return redirect(url_for("login", siguiente=request.path))
            if rol and session.get("rol") != rol:
                flash("No tiene permisos para esa acción.", "error")
                return redirect(url_for("inicio"))
            return vista(*args, **kwargs)
        return envoltura
    return decorador


# ------------------------------ Protección CSRF ------------------------------
def token_csrf():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


def campo_csrf():
    """Campo oculto que va dentro de cada <form method="post">."""
    return Markup(f'<input type="hidden" name="csrf" value="{token_csrf()}">')


@app.before_request
def validar_csrf():
    # Un sitio externo no puede enviar formularios en nombre del usuario
    if request.method == "POST" and request.form.get("csrf") != session.get("csrf"):
        abort(400, "Formulario vencido. Recargue la página e intente de nuevo.")


@app.context_processor
def variables_globales():
    tema = "claro"
    if "usuario" in session:
        try:
            tema = PreferenciaDAO.obtener(session["usuario"]).get("tema", "claro")
        except Exception:
            pass
    return {"tema": tema, "csrf": campo_csrf}


@app.template_filter("fecha")
def formato_fecha(valor, con_hora=True):
    if not hasattr(valor, "strftime"):
        return valor or "—"
    return valor.strftime("%d/%m/%Y %H:%M" if con_hora else "%d/%m/%Y")


@app.errorhandler(400)
def error_400(err):
    flash(err.description, "error")
    return redirect(request.referrer or url_for("inicio"))


@app.errorhandler(mysql.connector.errors.InterfaceError)
@app.errorhandler(mysql.connector.errors.PoolError)
def mysql_caido(err):
    return render_template("caida.html", detalle=str(err)), 503


# ------------------------------- Autenticación -------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        try:
            bloqueado = LogDAO.intentos_fallidos(username, MINUTOS_BLOQUEO) >= MAX_INTENTOS
        except Exception:
            bloqueado = False  # sin MongoDB no hay contador; se permite el intento
        if bloqueado:
            flash(f"Demasiados intentos fallidos. Espere {MINUTOS_BLOQUEO} minutos.", "error")
            return render_template("login.html", username=username)
        usuario = UsuarioDAO.autenticar(username, request.form.get("password", ""))
        if usuario:
            session.clear()
            session.update(
                usuario=usuario["Username"], rol=usuario["Rol"], id_estudiante=usuario["IdEstudiante"]
            )
            log("LOGIN_OK", {"ip": request.remote_addr})
            siguiente = request.args.get("siguiente", "")
            return redirect(siguiente if siguiente.startswith("/") and not siguiente.startswith("//") else url_for("inicio"))
        try:
            LogDAO.registrar(username or "anónimo", "LOGIN_FALLIDO", {"ip": request.remote_addr})
        except Exception:
            pass
        flash("Usuario o contraseña incorrectos.", "error")
        return render_template("login.html", username=username)
    return render_template("login.html")


@app.route("/logout")
def logout():
    log("LOGOUT")
    session.clear()
    flash("Sesión cerrada.", "ok")
    return redirect(url_for("login"))


@app.route("/cuenta", methods=["GET", "POST"])
@login_requerido()
def cuenta():
    if request.method == "POST":
        actual, nueva = request.form.get("actual", ""), request.form.get("nueva", "")
        if len(nueva) < 8:
            flash("La nueva contraseña debe tener al menos 8 caracteres.", "error")
        elif nueva != request.form.get("confirmar"):
            flash("La confirmación no coincide.", "error")
        elif UsuarioDAO.cambiar_password(session["usuario"], actual, nueva):
            log("CAMBIAR_PASSWORD")
            flash("Contraseña actualizada (se guardó solo su hash en MySQL).", "ok")
        else:
            flash("La contraseña actual no es correcta.", "error")
        return redirect(url_for("cuenta"))
    try:
        actividad = LogDAO.ultimos(10, usuario=session["usuario"])
        prefs = PreferenciaDAO.obtener(session["usuario"])
    except Exception:
        actividad, prefs = None, None
    return render_template("cuenta.html", actividad=actividad, prefs=prefs)


@app.route("/preferencias", methods=["POST"])
@login_requerido()
def preferencias():
    tema = "oscuro" if request.form.get("tema") == "oscuro" else "claro"
    try:
        PreferenciaDAO.guardar(session["usuario"], tema=tema)
        log("CAMBIAR_TEMA", {"tema": tema})
    except Exception:
        flash("MongoDB no está disponible: no se pudo guardar la preferencia.", "error")
    return redirect(request.referrer or url_for("inicio"))


# ---------------------------------- Panel ----------------------------------
@app.route("/")
@login_requerido()
def inicio():
    if session["rol"] != "ADMIN":
        return vista_estudiante(session["id_estudiante"])
    try:
        recientes, por_accion = LogDAO.ultimos(6), LogDAO.conteo_por_accion()[:6]
    except Exception:
        recientes, por_accion = None, None
    return render_template(
        "panel.html", resumen=resumen_bases(), por_estado=EstudianteDAO.por_estado(),
        cursos=CursoDAO.listar_con_estadisticas(), recientes=recientes, por_accion=por_accion,
    )


# -------------------------------- Estudiantes --------------------------------
@app.route("/estudiantes")
@login_requerido("ADMIN")
def estudiantes():
    q = request.args.get("q", "").strip()
    return render_template(
        "estudiantes.html", estudiantes=EstudianteDAO.listar(q or None), cursos=CursoDAO.listar(),
        todos=EstudianteDAO.listar(), q=q,
    )


@app.route("/estudiantes.csv")
@login_requerido("ADMIN")
def exportar_estudiantes():
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";")
    escritor.writerow(["Id", "Nombre", "Apellido", "FechaNacimiento", "Edad", "Email", "Promedio", "Estado"])
    for e in EstudianteDAO.listar(request.args.get("q") or None):
        escritor.writerow([
            e["IdEstudiante"], e["Nombre"], e["Apellido"], e["FechaNacimiento"], e["Edad"],
            e["Email"], e["Promedio"] if e["Promedio"] is not None else "", e["EstadoAcademico"],
        ])
    log("EXPORTAR_CSV")
    # BOM para que Excel abra bien las tildes
    return Response(
        "﻿" + salida.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=estudiantes_umb.csv"},
    )


@app.route("/estudiantes/nuevo", methods=["POST"])
@login_requerido("ADMIN")
def nuevo_estudiante():
    f = request.form
    try:
        nuevo_id = EstudianteDAO.insertar(
            f["nombre"].strip(), f["apellido"].strip(), date.fromisoformat(f["fecha"]), f["email"].strip()
        )
        log("CREAR_ESTUDIANTE", {"id": nuevo_id, "email": f["email"]})
        flash(f"Estudiante {nuevo_id} creado.", "ok")
        return redirect(url_for("detalle_estudiante", id_est=nuevo_id))
    except mysql.connector.IntegrityError:
        flash("Ya existe un estudiante con ese correo.", "error")
    except (mysql.connector.Error, ValueError) as err:
        flash(f"No se pudo crear: {getattr(err, 'msg', err)}", "error")
    return redirect(url_for("estudiantes"))


@app.route("/estudiantes/<int:id_est>")
@login_requerido("ADMIN")
def detalle_estudiante(id_est):
    if not EstudianteDAO.buscar_por_id(id_est):
        flash("El estudiante no existe.", "error")
        return redirect(url_for("estudiantes"))
    return vista_estudiante(id_est, admin=True)


@app.route("/estudiantes/<int:id_est>/editar", methods=["POST"])
@login_requerido("ADMIN")
def editar_estudiante(id_est):
    f = request.form
    try:
        if EstudianteDAO.actualizar(
            id_est, f["nombre"].strip(), f["apellido"].strip(), date.fromisoformat(f["fecha"]), f["email"].strip()
        ):
            log("EDITAR_ESTUDIANTE", {"id": id_est})
            flash("Datos actualizados en MySQL.", "ok")
        else:
            flash("El estudiante no existe.", "error")
    except mysql.connector.IntegrityError:
        flash("Ese correo ya lo usa otro estudiante.", "error")
    except (mysql.connector.Error, ValueError) as err:
        flash(f"No se pudo actualizar: {getattr(err, 'msg', err)}", "error")
    return redirect(url_for("detalle_estudiante", id_est=id_est))


@app.route("/estudiantes/<int:id_est>/eliminar", methods=["POST"])
@login_requerido("ADMIN")
def eliminar_estudiante(id_est):
    if not EstudianteDAO.eliminar(id_est):
        flash("El estudiante no existe.", "error")
        return redirect(url_for("estudiantes"))
    try:
        PerfilDAO.eliminar(id_est)  # borra también su documento en MongoDB
    except Exception:
        flash("Aviso: MongoDB no respondió; el perfil del estudiante quedó sin borrar.", "error")
    log("ELIMINAR_ESTUDIANTE", {"id": id_est})
    flash(f"Estudiante {id_est} eliminado de MySQL y MongoDB.", "ok")
    return redirect(url_for("estudiantes"))


@app.route("/estudiantes/<int:id_est>/cuenta", methods=["POST"])
@login_requerido("ADMIN")
def crear_cuenta(id_est):
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if len(username) < 3 or len(password) < 8:
        flash("Usuario de 3+ caracteres y contraseña de 8+ caracteres.", "error")
    elif UsuarioDAO.por_estudiante(id_est):
        flash("Este estudiante ya tiene cuenta.", "error")
    else:
        try:
            UsuarioDAO.crear(username, password, "ESTUDIANTE", id_est)
            log("CREAR_CUENTA", {"username": username, "id_estudiante": id_est})
            flash(f"Cuenta '{username}' creada. Ya puede iniciar sesión.", "ok")
        except mysql.connector.IntegrityError:
            flash("Ese nombre de usuario ya existe.", "error")
    return redirect(url_for("detalle_estudiante", id_est=id_est))


@app.route("/usuarios/<int:id_usuario>/estado", methods=["POST"])
@login_requerido("ADMIN")
def cambiar_estado_cuenta(id_usuario):
    activo = request.form.get("activo") == "1"
    UsuarioDAO.cambiar_estado(id_usuario, activo)
    log("ACTIVAR_CUENTA" if activo else "DESACTIVAR_CUENTA", {"id_usuario": id_usuario})
    flash("Cuenta activada." if activo else "Cuenta desactivada: ya no puede iniciar sesión.", "ok")
    return redirect(request.referrer or url_for("estudiantes"))


def perfil_seguro(id_est):
    try:
        return PerfilDAO.obtener(id_est), True
    except Exception:
        return {}, False  # MongoDB no disponible


def vista_estudiante(id_est, admin=False):
    """Une en una sola página los datos de MySQL (matrículas) y de MongoDB (perfil)."""
    est = EstudianteDAO.buscar_por_id(id_est)
    if not est:
        flash("Su usuario no está vinculado a un estudiante.", "error")
        return render_template("caida.html", detalle=None), 404
    matriculas = MatriculaDAO.por_estudiante(id_est)
    perfil, mongo_ok = perfil_seguro(id_est)
    # Fechas legibles en el JSON mostrado (hora local, sin la etiqueta GMT)
    perfil = {k: v.strftime("%Y-%m-%d %H:%M") if hasattr(v, "strftime") else v for k, v in perfil.items()}
    progreso = {
        "cursos": len(matriculas),
        "aprobados": sum(1 for m in matriculas if m["Estado"] == "APROBADO"),
        "creditos": sum(m["Creditos"] for m in matriculas if m["Estado"] == "APROBADO"),
        "creditos_total": sum(m["Creditos"] for m in matriculas),
    }
    ids_matriculados = {m["IdCurso"] for m in matriculas}
    return render_template(
        "estudiante.html", est=est, matriculas=matriculas, perfil=perfil, mongo_ok=mongo_ok,
        admin=admin, progreso=progreso,
        cuenta_usuario=UsuarioDAO.por_estudiante(id_est) if admin else None,
        cursos_libres=[c for c in CursoDAO.listar() if c["IdCurso"] not in ids_matriculados] if admin else [],
    )


@app.route("/estudiantes/<int:id_est>/perfil", methods=["POST"])
@login_requerido()
def guardar_perfil(id_est):
    # El estudiante solo puede editar SU perfil; el administrador, cualquiera
    if session["rol"] != "ADMIN" and session.get("id_estudiante") != id_est:
        flash("No tiene permisos para esa acción.", "error")
        return redirect(url_for("inicio"))
    est = EstudianteDAO.buscar_por_id(id_est)
    if not est:
        flash("El estudiante no existe.", "error")
        return redirect(url_for("inicio"))
    intereses = list(dict.fromkeys(i.strip() for i in request.form.get("intereses", "").split(",") if i.strip()))
    try:
        PerfilDAO.guardar(
            id_est, f"{est['Nombre']} {est['Apellido']}", intereses,
            request.form.get("semillero", "").strip() or None,
            request.form.get("github", "").strip().lstrip("@") or None,
        )
        log("EDITAR_PERFIL", {"id_estudiante": id_est, "intereses": intereses})
        flash("Perfil guardado en MongoDB.", "ok")
    except Exception as err:
        flash(f"MongoDB no disponible: {err}", "error")
    return redirect(request.referrer or url_for("inicio"))


# -------------------------------- Matrículas --------------------------------
@app.route("/matriculas/nueva", methods=["POST"])
@login_requerido("ADMIN")
def nueva_matricula():
    try:
        id_est, id_curso = int(request.form["id_estudiante"]), int(request.form["id_curso"])
    except (KeyError, ValueError):
        flash("Seleccione estudiante y curso.", "error")
        return redirect(request.referrer or url_for("estudiantes"))
    mensaje = MatriculaDAO.registrar(id_est, id_curso)
    log("MATRICULAR", {"id_estudiante": id_est, "id_curso": id_curso, "mensaje": mensaje})
    flash(mensaje, "ok" if mensaje.startswith("OK") else "error")
    return redirect(request.referrer or url_for("estudiantes"))


@app.route("/matriculas/<int:id_mat>/nota", methods=["POST"])
@login_requerido("ADMIN")
def poner_nota(id_mat):
    try:
        nota = float(request.form["nota"].replace(",", "."))
        if MatriculaDAO.poner_nota(id_mat, nota) == 0:
            flash(f"La matrícula {id_mat} no existe.", "error")
        else:
            log("PONER_NOTA", {"matricula": id_mat, "nota": nota})
            flash(f"Nota {nota:.1f} registrada. Estado y promedio recalculados con los SP.", "ok")
    except mysql.connector.Error as err:
        flash(f"Rechazada por la BD: {err.msg}", "error")  # trigger de validación 0.0–5.0
    except ValueError:
        flash("La nota debe ser un número.", "error")
    return redirect(request.referrer or url_for("inicio"))


@app.route("/recalcular", methods=["POST"])
@login_requerido("ADMIN")
def recalcular():
    matriculas, estudiantes_ = MatriculaDAO.recalcular_todo()
    log("RECALCULAR", {"matriculas": matriculas, "estudiantes": estudiantes_})
    flash(f"SP ejecutados: {matriculas} matrículas y {estudiantes_} estudiantes actualizados.", "ok")
    return redirect(request.referrer or url_for("inicio"))


@app.route("/matriculas/<int:id_mat>/retirar", methods=["POST"])
@login_requerido("ADMIN")
def retirar_matricula(id_mat):
    id_est = MatriculaDAO.retirar(id_mat)
    if id_est is None:
        flash(f"La matrícula {id_mat} no existe.", "error")
    else:
        log("RETIRAR_MATRICULA", {"matricula": id_mat, "id_estudiante": id_est})
        flash("Matrícula retirada y promedio recalculado.", "ok")
    return redirect(request.referrer or url_for("inicio"))


# ---------------------------------- Cursos ----------------------------------
@app.route("/cursos")
@login_requerido("ADMIN")
def cursos():
    return render_template("cursos.html", cursos=CursoDAO.listar_con_estadisticas())


@app.route("/cursos/nuevo", methods=["POST"])
@login_requerido("ADMIN")
def nuevo_curso():
    nombre = request.form.get("nombre", "").strip()
    try:
        creditos = int(request.form.get("creditos", ""))
        if not nombre or not 1 <= creditos <= 10:
            raise ValueError
        nuevo_id = CursoDAO.insertar(nombre, creditos)
        log("CREAR_CURSO", {"id": nuevo_id, "nombre": nombre})
        flash(f"Curso '{nombre}' creado.", "ok")
    except ValueError:
        flash("Escriba un nombre y entre 1 y 10 créditos.", "error")
    return redirect(url_for("cursos"))


@app.route("/cursos/<int:id_curso>")
@login_requerido("ADMIN")
def detalle_curso(id_curso):
    curso = CursoDAO.buscar_por_id(id_curso)
    if not curso:
        flash("El curso no existe.", "error")
        return redirect(url_for("cursos"))
    resumen, estudiantes_curso = CursoDAO.resumen(id_curso)  # sp_resumen_curso
    return render_template("curso.html", curso=curso, resumen=resumen, estudiantes=estudiantes_curso)


# ------------------------------ Auditoría y logs ------------------------------
@app.route("/auditoria")
@login_requerido("ADMIN")
def auditoria():
    return render_template("auditoria.html", filas=MatriculaDAO.auditoria())


@app.route("/logs")
@login_requerido("ADMIN")
def ver_logs():
    usuario, accion = request.args.get("usuario") or None, request.args.get("accion") or None
    try:
        logs = LogDAO.ultimos(100, usuario=usuario, accion=accion)
        conteo, usuarios = LogDAO.conteo_por_accion(), LogDAO.usuarios()
    except Exception as err:
        logs, conteo, usuarios = [], [], []
        flash(f"MongoDB no disponible: {err}", "error")
    return render_template(
        "logs.html", logs=logs, conteo=conteo, usuarios=usuarios, usuario=usuario, accion=accion,
    )


@app.route("/api/huella")
@login_requerido()
def huella():
    """La página la consulta cada 3 s: si cambió, otro programa modificó las bases."""
    return {"huella": huella_datos()}


if __name__ == "__main__":
    app.run(debug=False)
