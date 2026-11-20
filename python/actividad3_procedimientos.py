"""
ACTIVIDAD 3 – Llamada a procedimientos almacenados (Práctica 5) desde Python.

cursor.callproc(nombre, args) devuelve una tupla con los argumentos; en las
posiciones de los parámetros OUT quedan los valores que asignó el SP.
Los SELECT que hace el SP se leen con cursor.stored_results().

Ejecutar:  python actividad3_procedimientos.py
"""
import warnings

import mysql.connector

from conexion import conexion_mysql

# stored_results() funciona, pero el conector 9.x avisa que en el futuro será propiedad
warnings.filterwarnings("ignore", category=DeprecationWarning)


def registrar_matricula(cur, id_est, id_curso):
    # El tercer argumento es el OUT p_mensaje: se pasa un valor de relleno
    res = cur.callproc("sp_registrar_matricula", (id_est, id_curso, ""))
    print(f"  sp_registrar_matricula({id_est}, {id_curso}) -> OUT p_mensaje = {res[2]}")


def clasificar_estudiante(cur, id_est):
    # (IN id, OUT promedio, OUT clasificacion). Para OUT con tipo se usa (valor, 'TIPO')
    res = cur.callproc("sp_clasificar_estudiante", (id_est, (0, "DECIMAL(3,2)"), (0, "CHAR")))
    print(f"  Estudiante {id_est}: promedio = {res[1]}  clasificación = {res[2]}")


def actualizar_estados(cur, id_curso):
    res = cur.callproc("sp_actualizar_estados_curso", (id_curso, 0))
    print(f"  sp_actualizar_estados_curso({id_curso}) -> OUT p_procesados = {res[1]}")


def resumen_curso(cur, id_curso):
    res = cur.callproc("sp_resumen_curso", (id_curso, 0, (0, "DECIMAL(3,2)"), 0))
    print(f"  Curso {id_curso}: inscritos = {res[1]}, promedio = {res[2]}, aprobados = {res[3]}")
    # Result set devuelto por el SELECT interno del SP
    for resultado in cur.stored_results():
        for id_est, nombre, nota, estado in resultado.fetchall():
            print(f"     {id_est:<3} {nombre:<22} nota={str(nota):<5} {estado}")


def main():
    try:
        with conexion_mysql() as cnx:
            cur = cnx.cursor()

            print("\n1) sp_registrar_matricula  (IN, IN, OUT mensaje)")
            registrar_matricula(cur, 5, 2)    # válido
            registrar_matricula(cur, 99, 1)   # estudiante no existe
            registrar_matricula(cur, 1, 1)    # duplicado
            cnx.commit()

            print("\n2) sp_clasificar_estudiante  (IN, OUT promedio, OUT clasificación)")
            for id_est in range(1, 6):
                clasificar_estudiante(cur, id_est)
            cnx.commit()

            print("\n3) sp_actualizar_estados_curso  (IN, OUT procesados) – usa un CURSOR")
            actualizar_estados(cur, 1)
            cnx.commit()

            print("\n4) sp_resumen_curso  (IN, OUT, OUT, OUT + result set)")
            resumen_curso(cur, 1)

            print("\n5) Error controlado: SP que lanza SIGNAL")
            try:
                clasificar_estudiante(cur, 999)
            except mysql.connector.Error as err:
                print(f"  Capturado -> [{err.sqlstate}] {err.msg}")

            cur.close()
    except mysql.connector.Error as err:
        print(f"ERROR de MySQL [{err.errno}]: {err.msg}")


if __name__ == "__main__":
    main()
