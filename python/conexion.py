"""
conexion.py – Configuración y conexiones a MySQL y MongoDB.

Las credenciales se leen del archivo .env (o de variables de entorno),
nunca se escriben en el código fuente.
"""
import os
import sys
from contextlib import contextmanager

import mysql.connector
from mysql.connector import pooling
from mysql.connector.constants import ClientFlag
from dotenv import load_dotenv

# Tildes y símbolos correctos en la consola de Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Carga el .env que está junto a este archivo
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "app_umb"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "universidad_umb"),
    "charset": "utf8mb4",
    "collation": "utf8mb4_unicode_ci",
    # rowcount = filas ENCONTRADAS (no solo las que cambiaron) en UPDATE
    "client_flags": [ClientFlag.FOUND_ROWS],
}

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "universidad_umb_nosql")

_pool = None


def obtener_pool():
    """Crea (una sola vez) un pool de conexiones para reutilizarlas."""
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(pool_name="pool_umb", pool_size=5, **MYSQL_CONFIG)
    return _pool


@contextmanager
def conexion_mysql():
    """
    Gestor de contexto: entrega una conexión y la devuelve al pool SIEMPRE,
    aunque ocurra un error (evita fugas de conexiones).

        with conexion_mysql() as cnx:
            cur = cnx.cursor()
            ...
    """
    cnx = obtener_pool().get_connection()
    try:
        yield cnx
    finally:
        cnx.close()  # en un pool, close() devuelve la conexión al pool


_cliente_mongo = None


def base_mongo():
    """
    Devuelve la base de datos MongoDB (pymongo).
    MongoClient ya trae su propio pool de conexiones, así que se crea UNA sola
    vez y se reutiliza (crear un cliente por consulta es lento).
    """
    global _cliente_mongo
    if _cliente_mongo is None:
        from pymongo import MongoClient

        _cliente_mongo = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    return _cliente_mongo[MONGO_DB]
