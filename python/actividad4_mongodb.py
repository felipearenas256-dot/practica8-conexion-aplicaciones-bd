"""
ACTIVIDAD 4 – Conexión a MongoDB desde Python (pymongo).

CRUD básico sobre la colección 'estudiantes_perfil' (datos semiestructurados:
cada documento puede tener campos distintos): insert_one, find, update_one,
delete_one.

La URI se toma de MONGO_URI en el .env:
  - Atlas:  mongodb+srv://<usuario>:<clave>@<cluster>.mongodb.net/
  - Local:  mongodb://localhost:27017

Ejecutar:  python actividad4_mongodb.py
"""
from datetime import datetime

from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

from conexion import MONGO_DB, base_mongo


def mostrar(coleccion, titulo):
    print(f"\n{titulo}")
    for doc in coleccion.find({}, {"_id": 0}).sort("id_estudiante", 1):
        print("  ", doc)


def main():
    try:
        db = base_mongo()
        db.command("ping")  # verifica la conexión
        print(f"Conectado a MongoDB · base: {MONGO_DB}")

        perfiles = db.estudiantes_perfil
        perfiles.delete_many({})  # deja la colección limpia para la demostración

        # ---------- CREATE: insert_one ----------
        r1 = perfiles.insert_one({
            "id_estudiante": 1,                      # mismo ID que en MySQL
            "nombre": "Laura Gómez",
            "intereses": ["bases de datos", "IA"],
            "redes": {"github": "lgomez"},
            "creado": datetime.now(),
        })
        perfiles.insert_one({
            "id_estudiante": 2,
            "nombre": "Andrés Rodríguez",
            "intereses": ["redes"],
            "semillero": "Ciberseguridad",           # campo que el otro documento no tiene
            "creado": datetime.now(),
        })
        print(f"insert_one -> _id = {r1.inserted_id}")

        # ---------- READ: find ----------
        mostrar(perfiles, "find() – todos los perfiles:")
        print("\nfind({'intereses': 'IA'}):")
        for doc in perfiles.find({"intereses": "IA"}, {"_id": 0, "nombre": 1, "intereses": 1}):
            print("  ", doc)

        # ---------- UPDATE: update_one ----------
        r = perfiles.update_one(
            {"id_estudiante": 2},
            {"$push": {"intereses": "Python"}, "$set": {"actualizado": datetime.now()}},
        )
        print(f"\nupdate_one -> coincidencias = {r.matched_count}, modificados = {r.modified_count}")
        print("  ", perfiles.find_one({"id_estudiante": 2}, {"_id": 0}))

        # ---------- DELETE: delete_one ----------
        r = perfiles.delete_one({"id_estudiante": 1})
        print(f"\ndelete_one -> eliminados = {r.deleted_count}")
        mostrar(perfiles, "Estado final de la colección:")
        print(f"\nTotal de documentos: {perfiles.count_documents({})}")

    except ServerSelectionTimeoutError:
        print("ERROR: no se pudo conectar a MongoDB (revise MONGO_URI y el acceso de red en Atlas).")
    except PyMongoError as err:
        print(f"ERROR de MongoDB: {err}")


if __name__ == "__main__":
    main()
