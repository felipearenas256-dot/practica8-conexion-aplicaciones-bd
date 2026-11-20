"""
consola_sql.py – Consola donde se escriben CONSULTAS SQL (MySQL) o CÓDIGO PYTHON (MongoDB).

  - Si la línea empieza con una palabra SQL (SELECT, INSERT, UPDATE, DELETE, CALL,
    SHOW, DESCRIBE, ...) se ejecuta en MySQL. Termine con ;  (puede ocupar varias líneas).
  - Cualquier otra cosa se ejecuta como Python, con las colecciones de MongoDB listas:
    perfiles, logs, preferencias, db.

Los cambios se guardan al instante (autocommit) y la web los muestra sola en ~3 s.

Ejecutar:  python consola_sql.py
"""
import pprint
import re
import warnings

import mysql.connector
from bson import ObjectId
from pymongo.cursor import Cursor
from pymongo.command_cursor import CommandCursor

from conexion import MONGO_DB, MYSQL_CONFIG, base_mongo

warnings.filterwarnings("ignore", category=DeprecationWarning)

PALABRAS_SQL = {
    "SELECT", "INSERT", "UPDATE", "DELETE", "CALL", "SHOW", "DESCRIBE", "DESC", "USE", "SET",
    "WITH", "EXPLAIN", "START", "BEGIN", "COMMIT", "ROLLBACK", "CREATE", "DROP", "ALTER",
    "GRANT", "REPLACE", "TRUNCATE", "PREPARE", "EXECUTE", "DEALLOCATE",
}

AYUDA = f"""
================== CONSOLA SQL / PYTHON – PRÁCTICA 8 ==================
MySQL:   {MYSQL_CONFIG['database']} (usuario {MYSQL_CONFIG['user']})   ·   MongoDB: {MONGO_DB}

Escriba SQL (termina en ;) → se ejecuta en MySQL:
  SELECT * FROM Estudiante;
  SELECT * FROM Matricula WHERE IdEstudiante = 1;
  INSERT INTO Estudiante (Nombre, Apellido, FechaNacimiento, Email)
      VALUES ('Ana', 'Ríos', '2004-03-01', 'ana.rios@umb.edu.co');
  UPDATE Estudiante SET Nombre = 'Andrés Felipe' WHERE IdEstudiante = 2;
  UPDATE Matricula SET NotaFinal = 7 WHERE IdMatricula = 1;        -> ERROR del trigger
  CALL sp_clasificar_estudiante(1, @p, @c); SELECT @p, @c;
  CALL sp_registrar_matricula(5, 4, @m); SELECT @m;
  CALL sp_resumen_curso(1, @i, @pr, @a); SELECT @i, @pr, @a;
  SHOW TABLES;     DESCRIBE Estudiante;

Escriba Python → se ejecuta en MongoDB (colecciones: perfiles, logs, preferencias):
  perfiles.find()
  perfiles.find({{"id_estudiante": 1}})
  perfiles.insert_one({{"id_estudiante": 3, "nombre": "Camila Torres", "intereses": ["redes"]}})
  perfiles.update_one({{"id_estudiante": 3}}, {{"$push": {{"intereses": "Python"}}}})
  perfiles.delete_one({{"id_estudiante": 3}})
  logs.find().sort("fecha", -1).limit(5)
  logs.aggregate([{{"$group": {{"_id": "$accion", "total": {{"$sum": 1}}}}}}])
  perfiles.count_documents({{}})

Comandos:  ayuda   ·   tablas   ·   colecciones   ·   salir
=======================================================================
"""


# ------------------------------- MySQL -------------------------------
cnx = mysql.connector.connect(**MYSQL_CONFIG)
cnx.autocommit = True   # cada cambio queda guardado al instante (como Workbench)
# Una sola conexión para toda la sesión: las variables @p, @c de un CALL siguen vivas en el SELECT


def tabla(columnas, filas):
    if not filas:
        print("(0 filas)")
        return
    textos = [["NULL" if v is None else str(v) for v in f] for f in filas]
    anchos = [min(70, max(len(str(c)), *(len(t[i]) for t in textos))) for i, c in enumerate(columnas)]
    linea = "+" + "+".join("-" * (a + 2) for a in anchos) + "+"
    print(linea)
    print("| " + " | ".join(str(c)[:a].ljust(a) for c, a in zip(columnas, anchos)) + " |")
    print(linea)
    for t in textos:
        print("| " + " | ".join(v[:a].ljust(a) for v, a in zip(t, anchos)) + " |")
    print(linea)
    print(f"{len(filas)} fila(s)")


def dividir(texto):
    """Separa varias sentencias por ; respetando el texto entre comillas."""
    partes, actual, comilla = [], "", None
    for ch in texto:
        if comilla:
            if ch == comilla:
                comilla = None
        elif ch in ("'", '"'):
            comilla = ch
        elif ch == ";":
            if actual.strip():
                partes.append(actual.strip())
            actual = ""
            continue
        actual += ch
    if actual.strip():
        partes.append(actual.strip())
    return partes


def ejecutar_sql(texto):
    global cnx
    if not cnx.is_connected():
        cnx.reconnect(attempts=2, delay=1)
    for sentencia in dividir(texto):
        print(f"\nmysql> {sentencia};")
        try:
            cur = cnx.cursor()
            if re.match(r"(?is)^\s*CALL\b", sentencia):
                cur.execute(sentencia)
                # Un CALL puede devolver uno o varios result sets
                while True:
                    if cur.with_rows:
                        tabla([c[0] for c in cur.description], cur.fetchall())
                    if not cur.nextset():
                        break
                print("OK: procedimiento ejecutado (lea los OUT con SELECT @variable;)")
            else:
                cur.execute(sentencia)
                if cur.with_rows:
                    tabla([c[0] for c in cur.description], cur.fetchall())
                else:
                    extra = f" · nuevo Id = {cur.lastrowid}" if cur.lastrowid else ""
                    print(f"OK: {cur.rowcount} fila(s) afectada(s){extra}")
            cur.close()
        except mysql.connector.Error as err:
            print(f"ERROR {err.errno}: {err.msg}")
        except Exception as err:
            print(f"ERROR: {err}")


# ------------------------------ MongoDB ------------------------------
db = base_mongo()
entorno = {"db": db, "perfiles": db.estudiantes_perfil, "logs": db.logs, "preferencias": db.preferencias,
           "ObjectId": ObjectId}


def mostrar_mongo(resultado):
    if isinstance(resultado, (Cursor, CommandCursor)):
        docs = list(resultado)
        for d in docs:
            if isinstance(d.get("_id"), ObjectId):
                d.pop("_id")   # oculta el id interno; en un $group el _id es el dato agrupado
            print(" ", d)
        print(f"{len(docs)} documento(s)")
    elif hasattr(resultado, "inserted_id"):
        print(f"OK: insertado, _id = {resultado.inserted_id}")
    elif hasattr(resultado, "modified_count"):
        print(f"OK: coincidencias = {resultado.matched_count}, modificados = {resultado.modified_count}"
              + (f", creado = {resultado.upserted_id}" if resultado.upserted_id else ""))
    elif hasattr(resultado, "deleted_count"):
        print(f"OK: eliminados = {resultado.deleted_count}")
    elif resultado is not None:
        pprint.pprint(resultado, sort_dicts=False, width=110)


def ejecutar_python(codigo):
    print(f"\nmongo> {codigo}")
    try:
        try:
            mostrar_mongo(eval(codigo, entorno))
        except SyntaxError:
            exec(codigo, entorno)   # asignaciones, for, etc.
            print("OK")
    except Exception as err:
        print(f"ERROR: {type(err).__name__}: {err}")


# ------------------------------- Bucle -------------------------------
def es_sql(texto):
    primera = texto.lstrip().split(None, 1)[0].upper() if texto.strip() else ""
    return primera.rstrip(";") in PALABRAS_SQL


def main():
    print(AYUDA)
    while True:
        try:
            linea = input("\nsql/py> ")
        except (EOFError, KeyboardInterrupt):
            break
        texto = linea.strip()
        if not texto:
            continue
        orden = texto.lower().rstrip(";")
        if orden in ("salir", "exit", "quit"):
            break
        if orden == "ayuda":
            print(AYUDA)
            continue
        if orden == "tablas":
            ejecutar_sql("SHOW TABLES;")
            continue
        if orden == "colecciones":
            print(" ", db.list_collection_names())
            continue
        if es_sql(texto):
            # Si la sentencia no termina en ; se siguen leyendo líneas
            while not texto.rstrip().endswith(";"):
                try:
                    texto += "\n" + input("     -> ")
                except (EOFError, KeyboardInterrupt):
                    break
            ejecutar_sql(texto)
        else:
            ejecutar_python(texto)
    cnx.close()
    print("Conexiones cerradas. Hasta luego.")


if __name__ == "__main__":
    main()
