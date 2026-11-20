"""
dao.py – Patrón DAO (Data Access Object).

Cada clase concentra TODO el SQL de una tabla. El resto de la aplicación
(menú de consola, Flask) solo llama métodos como EstudianteDAO.listar()
y nunca escribe SQL. Todas las consultas son PARAMETRIZADAS (%s + tupla):
el conector envía los datos separados del SQL, así se evita la inyección.
"""
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from conexion import base_mongo, conexion_mysql


# ======================================================================
# MySQL
# ======================================================================
class EstudianteDAO:
    @staticmethod
    def listar():
        with conexion_mysql() as cnx:
            cur = cnx.cursor(dictionary=True)
            cur.execute(
                "SELECT IdEstudiante, Nombre, Apellido, FechaNacimiento, Email, "
                "Promedio, EstadoAcademico FROM Estudiante ORDER BY IdEstudiante"
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


class MatriculaDAO:
    @staticmethod
    def por_estudiante(id_estudiante):
        with conexion_mysql() as cnx:
            cur = cnx.cursor(dictionary=True)
            cur.execute(
                "SELECT m.IdMatricula, c.Nombre AS Curso, c.Creditos, m.FechaMatricula, "
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
        with conexion_mysql() as cnx:
            cur = cnx.cursor()
            cur.execute(
                "UPDATE Matricula SET NotaFinal = %s WHERE IdMatricula = %s", (nota, id_matricula)
            )
            cnx.commit()
            afectadas = cur.rowcount
            cur.close()
            return afectadas


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


# ======================================================================
# MongoDB – datos no estructurados (logs y preferencias)
# ======================================================================
class LogDAO:
    """Colección 'logs': un documento por acción realizada en la aplicación."""

    @staticmethod
    def registrar(usuario, accion, detalle=None):
        doc = {"usuario": usuario, "accion": accion, "fecha": datetime.now()}
        if detalle:
            doc["detalle"] = detalle  # campo libre: cada log puede traer datos distintos
        return base_mongo().logs.insert_one(doc).inserted_id

    @staticmethod
    def ultimos(limite=20, usuario=None):
        filtro = {"usuario": usuario} if usuario else {}
        return list(base_mongo().logs.find(filtro, {"_id": 0}).sort("fecha", -1).limit(limite))


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
        resumen["mongo"] = None  # MongoDB apagado: la app sigue funcionando con MySQL
    return resumen
