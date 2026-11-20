"""
consola_consultas.py – Consola interactiva para hacer consultas desde Python
a MySQL y MongoDB, ya conectada a las dos bases.

Ejecutar:  python -i consola_consultas.py
Luego escriba las consultas en el prompt >>>  (ejemplos al iniciar).
Todo lo que cambie aquí se refleja en la web, en Workbench y en Compass.
"""
import warnings
from datetime import datetime

import mysql.connector
from bson import ObjectId

from conexion import MONGO_DB, MYSQL_CONFIG, base_mongo, conexion_mysql

warnings.filterwarnings("ignore", category=DeprecationWarning)


def _tabla(columnas, filas):
    """Imprime filas como una tabla de texto."""
    if not filas:
        print("(sin filas)")
        return
    textos = [[("NULL" if v is None else str(v)) for v in f] for f in filas]
    anchos = [min(40, max(len(str(c)), *(len(t[i]) for t in textos))) for i, c in enumerate(columnas)]
    linea = "+" + "+".join("-" * (a + 2) for a in anchos) + "+"
    print(linea)
    print("| " + " | ".join(str(c)[:a].ljust(a) for c, a in zip(columnas, anchos)) + " |")
    print(linea)
    for t in textos:
        print("| " + " | ".join(v[:a].ljust(a) for v, a in zip(t, anchos)) + " |")
    print(linea)
    print(f"{len(filas)} fila(s)")


def sql(consulta, parametros=()):
    """
    Ejecuta una consulta MySQL PARAMETRIZADA.
      sql("SELECT * FROM Estudiante")
      sql("SELECT * FROM Estudiante WHERE IdEstudiante = %s", (1,))
      sql("UPDATE Estudiante SET Nombre = %s WHERE IdEstudiante = %s", ("Ana", 3))
    SELECT -> muestra la tabla.  INSERT/UPDATE/DELETE -> confirma (commit) y dice cuántas filas.
    """
    try:
        with conexion_mysql() as cnx:
            cur = cnx.cursor()
            cur.execute(consulta, parametros)
            if cur.description:  # devolvió filas
                _tabla([c[0] for c in cur.description], cur.fetchall())
            else:
                cnx.commit()
                extra = f" · nuevo Id = {cur.lastrowid}" if cur.lastrowid else ""
                print(f"OK: {cur.rowcount} fila(s) afectada(s){extra}")
            cur.close()
    except mysql.connector.Error as err:
        print(f"ERROR {err.errno}: {err.msg}")


def llamar(procedimiento, *argumentos):
    """
    Llama un procedimiento almacenado. Use None en cada parámetro OUT.
      llamar("sp_clasificar_estudiante", 1, None, None)
      llamar("sp_registrar_matricula", 5, 4, None)
      llamar("sp_resumen_curso", 1, None, None, None)
    """
    tipos = {"sp_clasificar_estudiante": {1: "DECIMAL(3,2)", 2: "CHAR"},
             "sp_resumen_curso": {2: "DECIMAL(3,2)"}}.get(procedimiento, {})
    # None = parámetro OUT: se pasa un valor de relleno (con su tipo si es decimal o texto)
    args = [a if a is not None else ((0, tipos[i]) if i in tipos else 0) for i, a in enumerate(argumentos)]
    try:
        with conexion_mysql() as cnx:
            cur = cnx.cursor()
            res = cur.callproc(procedimiento, args)
            for resultado in cur.stored_results():
                _tabla([c[0] for c in resultado.description], resultado.fetchall())
            cnx.commit()
            cur.close()
        salidas = {f"parámetro {i + 1}": res[i] for i, a in enumerate(argumentos) if a is None}
        print("OUT:", salidas)
    except mysql.connector.Error as err:
        print(f"ERROR {err.errno}: {err.msg}")


def ver(cursor_o_lista):
    """Muestra documentos de MongoDB, uno por línea: ver(perfiles.find())"""
    docs = list(cursor_o_lista) if not isinstance(cursor_o_lista, dict) else [cursor_o_lista]
    for d in docs:
        if isinstance(d.get("_id"), ObjectId):  # oculta el id interno; en un $group el _id es el dato agrupado
            d.pop("_id")
        print(" ", d)
    print(f"{len(docs)} documento(s)")


db = base_mongo()
perfiles = db.estudiantes_perfil
logs = db.logs
preferencias = db.preferencias

if __name__ == "__main__":  # el menú solo se muestra al abrir la consola, no al importarla
    print(f"""
================ CONSOLA DE CONSULTAS – PRÁCTICA 8 ================
MySQL:   {MYSQL_CONFIG['database']} (usuario {MYSQL_CONFIG['user']})
MongoDB: {MONGO_DB} (colecciones: perfiles, logs, preferencias)

MySQL (siempre con %s para los datos):
  sql("SELECT * FROM Estudiante")
  sql("SELECT * FROM Estudiante WHERE Apellido LIKE %s", ("%Gó%",))
  sql("INSERT INTO Estudiante (Nombre, Apellido, FechaNacimiento, Email) VALUES (%s, %s, %s, %s)",
      ("Ana", "Ríos", "2004-03-01", "ana.rios@umb.edu.co"))
  sql("UPDATE Estudiante SET Nombre = %s WHERE IdEstudiante = %s", ("Andrés Felipe", 2))
  sql("UPDATE Matricula SET NotaFinal = %s WHERE IdMatricula = %s", (7, 1))   -> ERROR del trigger
  llamar("sp_clasificar_estudiante", 1, None, None)
  llamar("sp_registrar_matricula", 5, 4, None)
  llamar("sp_resumen_curso", 1, None, None, None)

MongoDB:
  ver(perfiles.find())
  ver(perfiles.find({{"intereses": "IA"}}))
  perfiles.insert_one({{"id_estudiante": 3, "nombre": "Camila Torres", "intereses": ["redes"]}})
  perfiles.update_one({{"id_estudiante": 3}}, {{"$push": {{"intereses": "Python"}}}})
  perfiles.delete_one({{"id_estudiante": 3}})
  ver(logs.find().sort("fecha", -1).limit(5))
  ver(logs.aggregate([{{"$group": {{"_id": "$accion", "total": {{"$sum": 1}}}}}}]))

Salir: exit()
=================================================================
""")
