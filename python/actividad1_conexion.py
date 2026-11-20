"""
ACTIVIDAD 1 – Conexión básica Python–MySQL.

Muestra los 5 pasos: (1) instalar el conector, (2) conectar, (3) crear el
cursor, (4) ejecutar la consulta y leer resultados, (5) cerrar.
Incluye manejo de errores con try/except.

Ejecutar:  python actividad1_conexion.py
"""
import mysql.connector
from mysql.connector import errorcode

# (1) Instalado con: pip install mysql-connector-python
from conexion import MYSQL_CONFIG

cnx = None
cursor = None
try:
    # (2) Conectar
    cnx = mysql.connector.connect(**MYSQL_CONFIG)
    print(f"Conectado a MySQL {cnx.server_info} · base: {cnx.database} · usuario: {MYSQL_CONFIG['user']}")

    # (3) Crear el cursor
    cursor = cnx.cursor()

    # (4) Ejecutar un SELECT y mostrar los resultados
    cursor.execute(
        "SELECT IdEstudiante, Nombre, Apellido, Email, EstadoAcademico "
        "FROM Estudiante ORDER BY IdEstudiante"
    )
    filas = cursor.fetchall()

    print(f"\n{'ID':<4}{'Nombre':<15}{'Apellido':<15}{'Email':<32}{'Estado'}")
    print("-" * 78)
    for id_est, nombre, apellido, email, estado in filas:
        # [:14] recorta los textos largos para que las columnas no se descuadren
        print(f"{id_est:<4}{nombre[:14]:<15}{apellido[:14]:<15}{(email or '')[:31]:<32}{estado}")
    print(f"\nTotal de estudiantes: {cursor.rowcount}")

except mysql.connector.Error as err:
    # Errores típicos con mensaje claro
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("ERROR: usuario o contraseña incorrectos (revise el archivo .env).")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("ERROR: la base de datos no existe (ejecute sql/universidad_umb.sql).")
    elif err.errno == errorcode.CR_CONN_HOST_ERROR:
        print("ERROR: no se pudo conectar al servidor MySQL (¿está encendido?).")
    else:
        print(f"ERROR de MySQL [{err.errno}]: {err.msg}")

finally:
    # (5) Cerrar SIEMPRE cursor y conexión
    if cursor is not None:
        cursor.close()
    if cnx is not None and cnx.is_connected():
        cnx.close()
        print("Conexión cerrada.")
