"""
ACTIVIDAD 5 – Proyecto integrador: mini-aplicación web de gestión (Flask).

  - MySQL  -> datos transaccionales: estudiantes, cursos, matrículas, usuarios.
  - MongoDB -> datos no estructurados: logs de actividad y preferencias.
  - Autenticación básica con contraseñas hasheadas (tabla Usuario).
  - Todas las consultas parametrizadas (a través de dao.py).

Ejecutar:  python app.py   y abrir http://127.0.0.1:5000
Usuarios de prueba:  admin / Admin2026*   ·   lgomez / Laura2026*
"""
import os
from datetime import date
from functools import wraps

import mysql.connector
from flask import Flask, flash, redirect, render_template, request, session, url_for

from dao import (
    CursoDAO, EstudianteDAO, LogDAO, MatriculaDAO, PerfilDAO, PreferenciaDAO, UsuarioDAO, resumen_bases,
)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))


def log(accion, detalle=None):
    """Registra la acción en MongoDB; si Mongo no responde, la app sigue funcionando."""
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
                return redirect(url_for("login"))
            if rol and session.get("rol") != rol:
                flash("No tiene permisos para esa acción.", "error")
                return redirect(url_for("inicio"))
            return vista(*args, **kwargs)
        return envoltura
    return decorador


@app.context_processor
def preferencias_usuario():
    tema = "claro"
    if "usuario" in session:
        try:
            tema = PreferenciaDAO.obtener(session["usuario"]).get("tema", "claro")
        except Exception:
            pass
    return {"tema": tema}


# ------------------------------- Autenticación -------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        usuario = UsuarioDAO.autenticar(username, request.form.get("password", ""))
        if usuario:
            session.clear()
            session.update(
                usuario=usuario["Username"], rol=usuario["Rol"], id_estudiante=usuario["IdEstudiante"]
            )
            log("LOGIN_OK")
            return redirect(url_for("inicio"))
        try:
            LogDAO.registrar(username or "anónimo", "LOGIN_FALLIDO", {"ip": request.remote_addr})
        except Exception:
            pass
        flash("Usuario o contraseña incorrectos.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    log("LOGOUT")
    session.clear()
    return redirect(url_for("login"))


# --------------------------------- Vistas ---------------------------------
@app.route("/")
@login_requerido()
def inicio():
    if session["rol"] == "ADMIN":
        return render_template(
            "admin.html", estudiantes=EstudianteDAO.listar(), cursos=CursoDAO.listar(),
            resumen=resumen_bases(),
        )
    return vista_estudiante(session["id_estudiante"])


def perfil_seguro(id_est):
    try:
        return PerfilDAO.obtener(id_est), True
    except Exception:
        return {}, False  # MongoDB no disponible


def vista_estudiante(id_est, admin=False):
    """Une en una sola página los datos de MySQL (matrículas) y de MongoDB (perfil)."""
    est = EstudianteDAO.buscar_por_id(id_est)
    perfil, mongo_ok = perfil_seguro(id_est)
    # Fechas legibles en el JSON mostrado (hora local, sin la etiqueta GMT)
    perfil = {k: v.strftime("%Y-%m-%d %H:%M") if hasattr(v, "strftime") else v for k, v in perfil.items()}
    return render_template(
        "estudiante.html", est=est, matriculas=MatriculaDAO.por_estudiante(id_est),
        perfil=perfil, mongo_ok=mongo_ok, admin=admin,
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
    except (mysql.connector.Error, ValueError) as err:
        flash(f"No se pudo crear: {getattr(err, 'msg', err)}", "error")
    return redirect(url_for("inicio"))


@app.route("/estudiantes/<int:id_est>/eliminar", methods=["POST"])
@login_requerido("ADMIN")
def eliminar_estudiante(id_est):
    EstudianteDAO.eliminar(id_est)
    try:
        PerfilDAO.eliminar(id_est)  # borra también su documento en MongoDB
    except Exception:
        pass
    log("ELIMINAR_ESTUDIANTE", {"id": id_est})
    flash(f"Estudiante {id_est} eliminado.", "ok")
    return redirect(url_for("inicio"))


@app.route("/estudiantes/<int:id_est>")
@login_requerido("ADMIN")
def detalle_estudiante(id_est):
    est = EstudianteDAO.buscar_por_id(id_est)
    if not est:
        flash("El estudiante no existe.", "error")
        return redirect(url_for("inicio"))
    return vista_estudiante(id_est, admin=True)


@app.route("/matriculas/nueva", methods=["POST"])
@login_requerido("ADMIN")
def nueva_matricula():
    mensaje = MatriculaDAO.registrar(int(request.form["id_estudiante"]), int(request.form["id_curso"]))
    log("MATRICULAR", {"mensaje": mensaje})
    flash(mensaje, "ok" if mensaje.startswith("OK") else "error")
    return redirect(url_for("inicio"))


@app.route("/matriculas/<int:id_mat>/nota", methods=["POST"])
@login_requerido("ADMIN")
def poner_nota(id_mat):
    try:
        nota = float(request.form["nota"])
        if MatriculaDAO.poner_nota(id_mat, nota) == 0:
            flash(f"La matrícula {id_mat} no existe.", "error")
        else:
            log("PONER_NOTA", {"matricula": id_mat, "nota": nota})
            flash("Nota registrada.", "ok")
    except mysql.connector.Error as err:
        flash(f"Rechazada por la BD: {err.msg}", "error")  # trigger de validación 0.0–5.0
    except ValueError:
        flash("La nota debe ser un número.", "error")
    return redirect(request.referrer or url_for("inicio"))


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
    intereses = [i.strip() for i in request.form.get("intereses", "").split(",") if i.strip()]
    try:
        PerfilDAO.guardar(
            id_est, f"{est['Nombre']} {est['Apellido']}", intereses,
            request.form.get("semillero", "").strip() or None,
            request.form.get("github", "").strip() or None,
        )
        log("EDITAR_PERFIL", {"id_estudiante": id_est, "intereses": intereses})
        flash("Perfil guardado en MongoDB.", "ok")
    except Exception as err:
        flash(f"MongoDB no disponible: {err}", "error")
    return redirect(request.referrer or url_for("inicio"))


@app.route("/logs")
@login_requerido("ADMIN")
def ver_logs():
    try:
        logs = LogDAO.ultimos(50)
    except Exception as err:
        logs = []
        flash(f"MongoDB no disponible: {err}", "error")
    return render_template("logs.html", logs=logs)


@app.route("/preferencias", methods=["POST"])
@login_requerido()
def preferencias():
    tema = "oscuro" if request.form.get("tema") == "oscuro" else "claro"
    PreferenciaDAO.guardar(session["usuario"], tema=tema)
    log("CAMBIAR_TEMA", {"tema": tema})
    return redirect(request.referrer or url_for("inicio"))


if __name__ == "__main__":
    app.run(debug=False)
