"""
dao.py – Patrón DAO (Data Access Object).

Cada clase concentra TODO el SQL de una tabla. El resto del proyecto
(menú de consola, web Flask) solo llama métodos como EstudianteDAO.listar()
y nunca escribe SQL. Todas las consultas son PARAMETRIZADAS (%s + tupla):
el conector envía los datos separados del SQL, así se evita la inyección.
"""
import warnings
from datetime import datetime, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

from conexion import base_mongo, conexion_mysql


# ======================================================================
# MySQL
# ======================================================================
class EstudianteDAO:
    @staticmethod
    def listar(texto=None):
        """Lista todos o filtra por nombre, apellido o correo (búsqueda parametrizada)."""
        sql = (
            "SELECT IdEstudiante, Nombre, Apellido, FechaNacimiento, Email, Promedio, EstadoAcademico, "
            "fn_calcular_edad(FechaNacimiento) AS Edad FROM Estudiante"
        )
        params = ()
        if texto:
            sql += " WHERE CONCAT(Nombre, ' ', Apellido) LIKE %s OR Email LIKE %s"
            params = (f"%{texto}%", f"%{texto}%")
        with conexion_mysql() as cnx:
            cur = cnx.cursor(dictionary=True)
            cur.execute(sql + " ORDER BY IdEstudiante", params)
            filas = cur.fetchall()
            cur.close()
            return filas

    @staticmethod
    def por_estado():
        """Cuántos estudiantes hay en cada estado académico (para el panel)."""
        with conexion_mysql() as cnx:
            cur = cnx.cursor(dictionary=True)
            cur.execute(
                "SELECT EstadoAcademico AS estado, COUNT(*) AS total FROM Estudiante "
                "GROUP BY EstadoAcademico ORDER BY total DESC"
            )
            filas = cur.fetchall()
            cur.close()
            return filas

    @staticmethod
    def buscar_por_id(id_estudiante):
        with conexion_mysql() as cnx:
            cur = cnx.cursor(dictionary=True)
            cur.execute("SELECT * FROM Estudiante WHERE IdEstudiante = %s", (id_estudiante,))
            fila = cur.fetchone()
            cur.close()
            return fila

    @staticmethod
    def buscar_por_apellido(texto):
        with conexion_mysql() as cnx:
            cur = cnx.cursor(dictionary=True)
            # El comodín % va dentro del PARÁMETRO, no concatenado al SQL
            cur.execute(
                "SELECT IdEstudiante, Nombre, Apellido, FechaNacimiento, Email, Promedio, EstadoAcademico "
                "FROM Estudiante WHERE Apellido LIKE %s",
                (f"%{texto}%",),
            )
            filas = cur.fetchall()
            cur.close()
            return filas

    @staticmethod
    def insertar(nombre, apellido, fecha_nac, email):
        with conexion_mysql() as cnx:
            cur = cnx.cursor()
            cur.execute(
                "INSERT INTO Estudiante (Nombre, Apellido, FechaNacimiento, Email) "
                "VALUES (%s, %s, %s, %s)",
                (nombre, apellido, fecha_nac, email),
            )
            cnx.commit()
            nuevo_id = cur.lastrowid
            cur.close()
            return nuevo_id

    @staticmethod
    def actualizar(id_estudiante, nombre, apellido, fecha_nac, email):
        with conexion_mysql() as cnx:
            cur = cnx.cursor()
            cur.execute(
                "UPDATE Estudiante SET Nombre = %s, Apellido = %s, FechaNacimiento = %s, Email = %s "
                "WHERE IdEstudiante = %s",
                (nombre, apellido, fecha_nac, email, id_estudiante),
            )
            cnx.commit()
            afectadas = cur.rowcount
            cur.close()
            return afectadas

    @staticmethod
    def eliminar(id_estudiante):
        """Elimina al estudiante y sus matrículas dentro de UNA transacción."""
        with conexion_mysql() as cnx:
            cur = cnx.cursor()
            try:
                cnx.start_transaction()
                cur.execute("DELETE FROM Matricula WHERE IdEstudiante = %s", (id_estudiante,))
                cur.execute("DELETE FROM Estudiante WHERE IdEstudiante = %s", (id_estudiante,))
                afectadas = cur.rowcount
                cnx.commit()
                return afectadas
            except Exception:
                cnx.rollback()  # si algo falla no queda nada a medias
                raise
            finally:
                cur.close()


class CursoDAO:
    @staticmethod
    def listar():
        with conexion_mysql() as cnx:
            cur = cnx.cursor(dictionary=True)
            cur.execute("SELECT IdCurso, Nombre, Creditos FROM Curso ORDER BY IdCurso")
            filas = cur.fetchall()
            cur.close()
            return filas

    @staticmethod
    def listar_con_estadisticas():
        """LEFT JOIN + GROUP BY: cada curso con inscritos, promedio y aprobados."""
        with conexion_mysql() as cnx:
            cur = cnx.cursor(dictionary=True)
            cur.execute(
                "SELECT c.IdCurso, c.Nombre, c.Creditos, COUNT(m.IdMatricula) AS Inscritos, "
                "ROUND(AVG(m.NotaFinal), 2) AS Promedio, "
                "COALESCE(SUM(m.NotaFinal >= 3.0), 0) AS Aprobados "
                "FROM Curso c LEFT JOIN Matricula m ON m.IdCurso = c.IdCurso "
                "GROUP BY c.IdCurso, c.Nombre, c.Creditos ORDER BY c.IdCurso"
            )
            filas = cur.fetchall()
            cur.close()
            return filas

    @staticmethod
    def buscar_por_id(id_curso):
        with conexion_mysql() as cnx:
            cur = cnx.cursor(dictionary=True)
            cur.execute("SELECT IdCurso, Nombre, Creditos FROM Curso WHERE IdCurso = %s", (id_curso,))
            fila = cur.fetchone()
            cur.close()
            return fila

    @staticmethod
    def insertar(nombre, creditos):
        with conexion_mysql() as cnx:
            cur = cnx.cursor()
            cur.execute("INSERT INTO Curso (Nombre, Creditos) VALUES (%s, %s)", (nombre, creditos))
            cnx.commit()
            nuevo_id = cur.lastrowid
            cur.close()
            return nuevo_id

    @staticmethod
    def resumen(id_curso):
        """
        Llama a sp_resumen_curso: 3 parámetros OUT + un result set con los estudiantes.
        Devuelve (dict con los OUT, lista de estudiantes).
        """
        with conexion_mysql() as cnx:
            cur = cnx.cursor()
            res = cur.callproc("sp_resumen_curso", (id_curso, 0, (0, "DECIMAL(3,2)"), 0))
            filas = []
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                for resultado in cur.stored_results():
                    columnas = [c[0] for c in resultado.description]
                    filas += [dict(zip(columnas, f)) for f in resultado.fetchall()]
            cur.close()
        return {"inscritos": res[1], "promedio": res[2], "aprobados": res[3] or 0}, filas


class MatriculaDAO:
    @staticmethod
    def por_estudiante(id_estudiante):
        with conexion_mysql() as cnx:
            cur = cnx.cursor(dictionary=True)
            cur.execute(
                "SELECT m.IdMatricula, m.IdCurso, c.Nombre AS Curso, c.Creditos, m.FechaMatricula, "
                "m.NotaFinal, m.Estado "
                "FROM Matricula m JOIN Curso c ON c.IdCurso = m.IdCurso "
                "WHERE m.IdEstudiante = %s ORDER BY m.IdMatricula",
                (id_estudiante,),
            )
            filas = cur.fetchall()
            cur.close()
            return filas

    @staticmethod
    def registrar(id_estudiante, id_curso):
        """Usa el SP de la Práctica 5 (valida y audita). Devuelve el mensaje OUT."""
        with conexion_mysql() as cnx:
            cur = cnx.cursor()
            resultado = cur.callproc("sp_registrar_matricula", (id_estudiante, id_curso, ""))
            cnx.commit()
            cur.close()
            return resultado[2]

    @staticmethod
    def poner_nota(id_matricula, nota):
        """
        Guarda la nota (el trigger valida 0.0–5.0) y luego reutiliza los SP de la
        Práctica 5 para que el estado de la matrícula y el promedio del estudiante
        queden al día. Devuelve las filas encontradas (0 = la matrícula no existe).
        """
        with conexion_mysql() as cnx:
            cur = cnx.cursor()
            try:
                cnx.start_transaction()
                cur.execute(
                    "UPDATE Matricula SET NotaFinal = %s WHERE IdMatricula = %s", (nota, id_matricula)
                )
                afectadas = cur.rowcount
                if afectadas:
                    cur.execute(
                        "SELECT IdEstudiante, IdCurso FROM Matricula WHERE IdMatricula = %s", (id_matricula,)
                    )
                    id_est, id_curso = cur.fetchone()
                    cur.callproc("sp_actualizar_estados_curso", (id_curso, 0))
                    cur.callproc("sp_clasificar_estudiante", (id_est, (0, "DECIMAL(3,2)"), (0, "CHAR")))
                cnx.commit()
                return afectadas
            except Exception:
                cnx.rollback()
                raise
            finally:
                cur.close()

    @staticmethod
    def recalcular_todo():
        """
        Ejecuta los SP de la Práctica 5 sobre toda la base:
        sp_actualizar_estados_curso (cursor) por cada curso y
        sp_clasificar_estudiante por cada estudiante. Devuelve (matrículas, estudiantes).
        """
        with conexion_mysql() as cnx:
            cur = cnx.cursor()
            try:
                cnx.start_transaction()
                cur.execute("SELECT IdCurso FROM Curso")
                cursos = [f[0] for f in cur.fetchall()]
                cur.execute("SELECT IdEstudiante FROM Estudiante")
                estudiantes = [f[0] for f in cur.fetchall()]
                procesadas = sum(cur.callproc("sp_actualizar_estados_curso", (c, 0))[1] for c in cursos)
                for e in estudiantes:
                    cur.callproc("sp_clasificar_estudiante", (e, (0, "DECIMAL(3,2)"), (0, "CHAR")))
                cnx.commit()
                return procesadas, len(estudiantes)
            except Exception:
                cnx.rollback()
                raise
            finally:
                cur.close()

    @staticmethod
    def retirar(id_matricula):
        """Elimina una matrícula y recalcula el promedio del estudiante (una transacción)."""
        with conexion_mysql() as cnx:
            cur = cnx.cursor()
            try:
                cnx.start_transaction()
                cur.execute("SELECT IdEstudiante FROM Matricula WHERE IdMatricula = %s", (id_matricula,))
                fila = cur.fetchone()
                if not fila:
                    cnx.rollback()
                    return None
                cur.execute("DELETE FROM Matricula WHERE IdMatricula = %s", (id_matricula,))
                cur.callproc("sp_clasificar_estudiante", (fila[0], (0, "DECIMAL(3,2)"), (0, "CHAR")))
                cnx.commit()
                return fila[0]
            except Exception:
                cnx.rollback()
                raise
            finally:
                cur.close()

    @staticmethod
    def auditoria(limite=100):
        """Tabla Auditoria_Matricula (la llena el trigger AFTER INSERT)."""
        with conexion_mysql() as cnx:
            cur = cnx.cursor(dictionary=True)
            cur.execute(
                "SELECT a.IdAuditoria, a.IdMatricula, a.Accion, a.Usuario, a.FechaHora, "
                "COALESCE(fn_formatear_nombre(e.Nombre, e.Apellido), CONCAT('Estudiante ', a.IdEstudiante)) AS Estudiante, "
                "COALESCE(c.Nombre, CONCAT('Curso ', a.IdCurso)) AS Curso "
                "FROM Auditoria_Matricula a "
                "LEFT JOIN Estudiante e ON e.IdEstudiante = a.IdEstudiante "
                "LEFT JOIN Curso c ON c.IdCurso = a.IdCurso "
                "ORDER BY a.IdAuditoria DESC LIMIT %s",
                (limite,),
            )
            filas = cur.fetchall()
            cur.close()
            return filas


class UsuarioDAO:
    @staticmethod
    def crear(username, password, rol="ESTUDIANTE", id_estudiante=None):
        """Guarda solo el HASH de la contraseña (scrypt + sal), nunca el texto plano."""
        with conexion_mysql() as cnx:
            cur = cnx.cursor()
            cur.execute(
                "INSERT INTO Usuario (Username, PasswordHash, Rol, IdEstudiante) VALUES (%s, %s, %s, %s)",
                (username, generate_password_hash(password), rol, id_estudiante),
            )
            cnx.commit()
            nuevo_id = cur.lastrowid
            cur.close()
            return nuevo_id

    @staticmethod
    def autenticar(username, password):
        """Devuelve el usuario si las credenciales son correctas; si no, None."""
        with conexion_mysql() as cnx:
            cur = cnx.cursor(dictionary=True)
            cur.execute(
                "SELECT IdUsuario, Username, PasswordHash, Rol, IdEstudiante "
                "FROM Usuario WHERE Username = %s AND Activo = TRUE",
                (username,),
            )
            usuario = cur.fetchone()
            cur.close()
        if usuario and check_password_hash(usuario["PasswordHash"], password):
            usuario.pop("PasswordHash")
            return usuario
        return None

    @staticmethod
    def por_estudiante(id_estudiante):
        with conexion_mysql() as cnx:
            cur = cnx.cursor(dictionary=True)
            cur.execute(
                "SELECT IdUsuario, Username, Rol, Activo, FechaCreacion FROM Usuario WHERE IdEstudiante = %s",
                (id_estudiante,),
            )
            fila = cur.fetchone()
            cur.close()
            return fila

    @staticmethod
    def cambiar_estado(id_usuario, activo):
        with conexion_mysql() as cnx:
            cur = cnx.cursor()
            cur.execute("UPDATE Usuario SET Activo = %s WHERE IdUsuario = %s", (activo, id_usuario))
            cnx.commit()
            cur.close()

    @staticmethod
    def cambiar_password(username, actual, nueva):
        """Comprueba la contraseña actual y guarda el hash de la nueva. True si cambió."""
        if not UsuarioDAO.autenticar(username, actual):
            return False
        with conexion_mysql() as cnx:
            cur = cnx.cursor()
            cur.execute(
                "UPDATE Usuario SET PasswordHash = %s WHERE Username = %s",
                (generate_password_hash(nueva), username),
            )
            cnx.commit()
            cur.close()
        return True


# ======================================================================
# MongoDB – datos no estructurados (logs y preferencias)
# ======================================================================
class LogDAO:
    """Colección 'logs': un documento por acción realizada en la web."""

    @staticmethod
    def registrar(usuario, accion, detalle=None):
        doc = {"usuario": usuario, "accion": accion, "fecha": datetime.now()}
        if detalle:
            doc["detalle"] = detalle  # campo libre: cada log puede traer datos distintos
        return base_mongo().logs.insert_one(doc).inserted_id

    @staticmethod
    def ultimos(limite=20, usuario=None, accion=None):
        filtro = {}
        if usuario:
            filtro["usuario"] = usuario
        if accion:
            filtro["accion"] = accion
        return list(base_mongo().logs.find(filtro, {"_id": 0}).sort("fecha", -1).limit(limite))

    @staticmethod
    def conteo_por_accion():
        """Pipeline de agregación: cuántas veces ocurrió cada acción."""
        return list(base_mongo().logs.aggregate([
            {"$group": {"_id": "$accion", "total": {"$sum": 1}}},
            {"$sort": {"total": -1}},
        ]))

    @staticmethod
    def usuarios():
        return sorted(u for u in base_mongo().logs.distinct("usuario") if u)

    @staticmethod
    def intentos_fallidos(usuario, minutos=10):
        """
        Intentos fallidos de login en los últimos N minutos, contados desde el
        último ingreso correcto. Se usa para frenar ataques de fuerza bruta.
        """
        logs = base_mongo().logs
        desde = datetime.now() - timedelta(minutes=minutos)
        ultimo_ok = logs.find_one({"usuario": usuario, "accion": "LOGIN_OK"}, sort=[("fecha", -1)])
        if ultimo_ok and ultimo_ok["fecha"] > desde:
            desde = ultimo_ok["fecha"]
        return logs.count_documents({"usuario": usuario, "accion": "LOGIN_FALLIDO", "fecha": {"$gt": desde}})


class PreferenciaDAO:
    """Colección 'preferencias': un documento por usuario, con campos libres."""

    @staticmethod
    def obtener(usuario):
        doc = base_mongo().preferencias.find_one({"usuario": usuario}, {"_id": 0})
        return doc or {"usuario": usuario, "tema": "claro", "idioma": "es"}

    @staticmethod
    def guardar(usuario, **cambios):
        base_mongo().preferencias.update_one(
            {"usuario": usuario}, {"$set": cambios}, upsert=True
        )


class PerfilDAO:
    """
    Colección 'estudiantes_perfil' (la misma de la Actividad 4): datos libres
    del estudiante que no encajan en una tabla fija (intereses, redes, semillero...).
    Se enlaza con MySQL por el campo id_estudiante.
    """

    @staticmethod
    def obtener(id_estudiante):
        return base_mongo().estudiantes_perfil.find_one({"id_estudiante": id_estudiante}, {"_id": 0}) or {}

    @staticmethod
    def guardar(id_estudiante, nombre, intereses, semillero=None, github=None):
        datos = {"nombre": nombre, "intereses": intereses, "actualizado": datetime.now()}
        quitar = {}
        # Solo se guardan los campos que tienen valor: cada documento puede ser distinto
        for campo, valor in (("semillero", semillero), ("redes", {"github": github} if github else None)):
            if valor:
                datos[campo] = valor
            else:
                quitar[campo] = ""
        cambios = {"$set": datos}
        if quitar:
            cambios["$unset"] = quitar
        base_mongo().estudiantes_perfil.update_one({"id_estudiante": id_estudiante}, cambios, upsert=True)

    @staticmethod
    def eliminar(id_estudiante):
        base_mongo().estudiantes_perfil.delete_one({"id_estudiante": id_estudiante})


def resumen_bases():
    """Conteos de las dos bases para el panel del administrador."""
    with conexion_mysql() as cnx:
        cur = cnx.cursor()
        cur.execute(
            "SELECT (SELECT COUNT(*) FROM Estudiante), (SELECT COUNT(*) FROM Curso), "
            "(SELECT COUNT(*) FROM Matricula), (SELECT COUNT(*) FROM Usuario)"
        )
        est, cur_, mat, usu = cur.fetchone()
        cur.close()
    resumen = {"mysql": {"Estudiantes": est, "Cursos": cur_, "Matrículas": mat, "Usuarios": usu}}
    try:
        db = base_mongo()
        resumen["mongo"] = {
            "Perfiles": db.estudiantes_perfil.count_documents({}),
            "Logs": db.logs.count_documents({}),
            "Preferencias": db.preferencias.count_documents({}),
        }
    except Exception:
        resumen["mongo"] = None  # MongoDB apagado: la web sigue funcionando con MySQL
    return resumen
