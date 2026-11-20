"""
consultas_python.py – Las consultas de la práctica hechas DESDE PYTHON,
organizadas por bloques (como sql/consultas_procedimientos.sql en Workbench).

Ejecutar todo:        python consultas_python.py
Ejecutar un bloque:   python consultas_python.py B      (bloques: A B C D E F)

Cada consulta se imprime antes de ejecutarse y dice si debe dar OK o ERROR.
Lo que cambie aquí se ve en la web (sola, en ~3 s), en Workbench y en Compass.
"""
import sys

from consola_consultas import llamar, logs, perfiles, sql, ver


def titulo(texto):
    print("\n" + "=" * 70 + f"\n {texto}\n" + "=" * 70)


def consulta(descripcion, esperado="OK"):
    print(f"\n>>> {descripcion}   [se espera: {esperado}]")


# ---------------------------------------------------------------------
def bloque_a():
    titulo("A. CONSULTAS MySQL (SELECT parametrizado)")

    consulta('sql("SELECT IdEstudiante, Nombre, Apellido, Promedio, EstadoAcademico FROM Estudiante")')
    sql("SELECT IdEstudiante, Nombre, Apellido, Promedio, EstadoAcademico FROM Estudiante")

    consulta('sql("SELECT ... WHERE IdEstudiante = %s", (1,))')
    sql("SELECT IdEstudiante, Nombre, Apellido, Email FROM Estudiante WHERE IdEstudiante = %s", (1,))

    consulta('sql("SELECT ... WHERE Apellido LIKE %s", ("%Gó%",))')
    sql("SELECT IdEstudiante, Nombre, Apellido FROM Estudiante WHERE Apellido LIKE %s", ("%Gó%",))

    consulta("JOIN: matrículas con el nombre del estudiante y del curso")
    sql("SELECT m.IdMatricula, CONCAT(e.Nombre, ' ', e.Apellido) AS estudiante, c.Nombre AS curso, "
        "m.NotaFinal, m.Estado FROM Matricula m "
        "JOIN Estudiante e ON e.IdEstudiante = m.IdEstudiante "
        "JOIN Curso c ON c.IdCurso = m.IdCurso WHERE m.IdEstudiante = %s", (1,))

    consulta("GROUP BY: inscritos y promedio por curso")
    sql("SELECT c.Nombre AS curso, COUNT(m.IdMatricula) AS inscritos, ROUND(AVG(m.NotaFinal), 2) AS promedio "
        "FROM Curso c LEFT JOIN Matricula m ON m.IdCurso = c.IdCurso GROUP BY c.IdCurso, c.Nombre")


# ---------------------------------------------------------------------
def bloque_b():
    titulo("B. PROCEDIMIENTOS ALMACENADOS (callproc, None = parámetro OUT)")

    consulta('llamar("sp_clasificar_estudiante", 1, None, None)  -> OUT promedio, clasificación')
    llamar("sp_clasificar_estudiante", 1, None, None)

    consulta('llamar("sp_registrar_matricula", 5, 4, None)  -> OUT mensaje',
             "OK la primera vez; ERROR del SP si ya está matriculado")
    llamar("sp_registrar_matricula", 5, 4, None)

    consulta('llamar("sp_registrar_matricula", 1, 1, None)', "ERROR del SP: ya está matriculado")
    llamar("sp_registrar_matricula", 1, 1, None)

    consulta('llamar("sp_actualizar_estados_curso", 1, None)  -> OUT procesados (usa un CURSOR)')
    llamar("sp_actualizar_estados_curso", 1, None)

    consulta('llamar("sp_resumen_curso", 1, None, None, None)  -> result set + 3 OUT')
    llamar("sp_resumen_curso", 1, None, None, None)

    consulta('llamar("sp_clasificar_estudiante", 999, None, None)', "ERROR 1644: El estudiante no existe.")
    llamar("sp_clasificar_estudiante", 999, None, None)

    consulta("Funciones: fn_formatear_nombre y fn_calcular_edad")
    sql("SELECT IdEstudiante, fn_formatear_nombre(Nombre, Apellido) AS nombre, "
        "fn_calcular_edad(FechaNacimiento) AS edad FROM Estudiante")


# ---------------------------------------------------------------------
def bloque_c():
    titulo("C. INSERT / UPDATE / DELETE en MySQL (se deshacen al final)")

    consulta("INSERT de un estudiante")
    sql("INSERT INTO Estudiante (Nombre, Apellido, FechaNacimiento, Email) VALUES (%s, %s, %s, %s)",
        ("Ana", "Ríos", "2004-03-01", "ana.rios.demo@umb.edu.co"))
    sql("SELECT IdEstudiante, Nombre, Apellido, Email FROM Estudiante WHERE Email = %s", ("ana.rios.demo@umb.edu.co",))

    consulta("UPDATE del nombre")
    sql("UPDATE Estudiante SET Nombre = %s WHERE Email = %s", ("Ana María", "ana.rios.demo@umb.edu.co"))

    consulta("DELETE del estudiante de prueba")
    sql("DELETE FROM Estudiante WHERE Email = %s", ("ana.rios.demo@umb.edu.co",))


# ---------------------------------------------------------------------
def bloque_d():
    titulo("D. ERRORES ESPERADOS (la base protege los datos)")

    consulta("UPDATE Matricula SET NotaFinal = 7", "ERROR 1644 del trigger")
    sql("UPDATE Matricula SET NotaFinal = %s WHERE IdMatricula = %s", (7, 1))

    consulta("INSERT de matrícula repetida (1, 1)", "ERROR 1062 Duplicate entry")
    sql("INSERT INTO Matricula (IdEstudiante, IdCurso, FechaMatricula) VALUES (%s, %s, CURDATE())", (1, 1))

    consulta("INSERT de matrícula para un estudiante que no existe", "ERROR 1216 clave foránea (con root sale como 1452)")
    sql("INSERT INTO Matricula (IdEstudiante, IdCurso, FechaMatricula) VALUES (%s, %s, CURDATE())", (999, 1))

    consulta("DELETE de un estudiante con matrículas", "ERROR 1217 clave foránea (con root sale como 1451)")
    sql("DELETE FROM Estudiante WHERE IdEstudiante = %s", (1,))

    consulta("DROP TABLE con el usuario app_umb", "ERROR 1142 sin permiso")
    sql("DROP TABLE Curso")


# ---------------------------------------------------------------------
def bloque_e():
    titulo("E. INYECCIÓN SQL: concatenada vs parametrizada")
    entrada = "x' OR '1'='1"

    consulta(f"CONCATENADA: ... WHERE Apellido = '{entrada}'", "VULNERABLE: devuelve toda la tabla")
    sql(f"SELECT IdEstudiante, Nombre, Apellido FROM Estudiante WHERE Apellido = '{entrada}'")

    consulta("PARAMETRIZADA: ... WHERE Apellido = %s", "SEGURA: 0 filas")
    sql("SELECT IdEstudiante, Nombre, Apellido FROM Estudiante WHERE Apellido = %s", (entrada,))


# ---------------------------------------------------------------------
def bloque_f():
    titulo("F. MongoDB (pymongo)")

    consulta('ver(perfiles.find())')
    ver(perfiles.find())

    consulta('ver(perfiles.find({"id_estudiante": 1}))')
    ver(perfiles.find({"id_estudiante": 1}))

    consulta('perfiles.update_one({"id_estudiante": 1}, {"$addToSet": {"intereses": "MongoDB"}})')
    r = perfiles.update_one({"id_estudiante": 1}, {"$addToSet": {"intereses": "MongoDB"}})
    print(f"OK: coincidencias = {r.matched_count}, modificados = {r.modified_count}")

    consulta('perfiles.update_one({"id_estudiante": 1}, {"$pull": {"intereses": "MongoDB"}})  (lo deshace)')
    r = perfiles.update_one({"id_estudiante": 1}, {"$pull": {"intereses": "MongoDB"}})
    print(f"OK: coincidencias = {r.matched_count}, modificados = {r.modified_count}")

    consulta('ver(logs.find({}, {"usuario": 1, "accion": 1, "fecha": 1}).sort("fecha", -1).limit(5))')
    ver(logs.find({}, {"usuario": 1, "accion": 1, "fecha": 1}).sort("fecha", -1).limit(5))

    consulta('logs.aggregate([$group por acción, $sort])')
    ver(logs.aggregate([{"$group": {"_id": "$accion", "total": {"$sum": 1}}}, {"$sort": {"total": -1}}]))

    consulta('perfiles.count_documents({})')
    print(f"OK: {perfiles.count_documents({})} documento(s)")


BLOQUES = {"A": bloque_a, "B": bloque_b, "C": bloque_c, "D": bloque_d, "E": bloque_e, "F": bloque_f}

if __name__ == "__main__":
    elegidos = [b.upper() for b in sys.argv[1:]] or list(BLOQUES)
    for b in elegidos:
        BLOQUES[b]()
