"""
Demostración de seguridad: consulta concatenada (VULNERABLE) vs parametrizada (SEGURA).

Ejecutar:  python demo_inyeccion.py
"""
from conexion import conexion_mysql

entrada_maliciosa = "x' OR '1'='1"

with conexion_mysql() as cnx:
    cur = cnx.cursor()

    # MAL: el dato se pega dentro del SQL -> la comilla cierra el texto y OR '1'='1' es siempre verdadero
    sql_vulnerable = f"SELECT IdEstudiante, Nombre, Apellido FROM Estudiante WHERE Apellido = '{entrada_maliciosa}'"
    print("VULNERABLE:", sql_vulnerable)
    cur.execute(sql_vulnerable)
    print(f"  -> devolvió {len(cur.fetchall())} filas (¡toda la tabla!)\n")

    # BIEN: el dato viaja aparte; MySQL lo compara como texto literal
    print("SEGURA:     SELECT ... WHERE Apellido = %s   con parámetro", repr(entrada_maliciosa))
    cur.execute("SELECT IdEstudiante, Nombre, Apellido FROM Estudiante WHERE Apellido = %s", (entrada_maliciosa,))
    print(f"  -> devolvió {len(cur.fetchall())} filas")

    cur.close()
