"""
ACTIVIDAD 2 – CRUD completo desde Python con menú en consola.

Todas las operaciones pasan por EstudianteDAO (dao.py), que usa SOLO
consultas parametrizadas.

Ejecutar:  python actividad2_crud.py
"""
from datetime import date

import mysql.connector

from dao import EstudianteDAO, UsuarioDAO


def pedir_fecha(mensaje):
    while True:
        texto = input(mensaje).strip()
        try:
            return date.fromisoformat(texto)
        except ValueError:
            print("  Formato inválido, use AAAA-MM-DD.")


def pedir_entero(mensaje):
    while True:
        texto = input(mensaje).strip()
        if texto.isdigit():
            return int(texto)
        print("  Debe ser un número entero.")


def imprimir_estudiantes(filas):
    if not filas:
        print("  (sin resultados)")
        return
    print(f"\n  {'ID':<4}{'Nombre':<12}{'Apellido':<12}{'Nacimiento':<12}{'Email':<32}{'Prom.':<7}{'Estado'}")
    print("  " + "-" * 90)
    for e in filas:
        prom = "" if e.get("Promedio") is None else str(e["Promedio"])
        print(
            f"  {e['IdEstudiante']:<4}{e['Nombre']:<12}{e['Apellido']:<12}"
            f"{str(e.get('FechaNacimiento', '')):<12}{e.get('Email') or '':<32}{prom:<7}{e.get('EstadoAcademico', '')}"
        )


# ---------------------------- Operaciones CRUD ----------------------------
def crear():
    print("\n-- Insertar estudiante --")
    nombre = input("  Nombre: ").strip()
    apellido = input("  Apellido: ").strip()
    fecha = pedir_fecha("  Fecha de nacimiento (AAAA-MM-DD): ")
    email = input("  Email: ").strip() or None
    nuevo_id = EstudianteDAO.insertar(nombre, apellido, fecha, email)
    print(f"  OK: estudiante creado con ID {nuevo_id}.")


def consultar():
    print("\n-- Consultar --\n  1. Todos\n  2. Por ID\n  3. Por apellido")
    opcion = input("  Opción: ").strip()
    if opcion == "1":
        imprimir_estudiantes(EstudianteDAO.listar())
    elif opcion == "2":
        est = EstudianteDAO.buscar_por_id(pedir_entero("  ID: "))
        imprimir_estudiantes([est] if est else [])
    elif opcion == "3":
        imprimir_estudiantes(EstudianteDAO.buscar_por_apellido(input("  Apellido contiene: ").strip()))


def actualizar():
    print("\n-- Actualizar estudiante --")
    id_est = pedir_entero("  ID a modificar: ")
    actual = EstudianteDAO.buscar_por_id(id_est)
    if not actual:
        print("  No existe un estudiante con ese ID.")
        return
    print("  (Enter = dejar el valor actual)")
    nombre = input(f"  Nombre [{actual['Nombre']}]: ").strip() or actual["Nombre"]
    apellido = input(f"  Apellido [{actual['Apellido']}]: ").strip() or actual["Apellido"]
    texto_fecha = input(f"  Nacimiento [{actual['FechaNacimiento']}]: ").strip()
    fecha = date.fromisoformat(texto_fecha) if texto_fecha else actual["FechaNacimiento"]
    email = input(f"  Email [{actual['Email']}]: ").strip() or actual["Email"]
    n = EstudianteDAO.actualizar(id_est, nombre, apellido, fecha, email)
    print(f"  OK: {n} fila(s) actualizada(s).")


def eliminar():
    print("\n-- Eliminar estudiante --")
    id_est = pedir_entero("  ID a eliminar: ")
    est = EstudianteDAO.buscar_por_id(id_est)
    if not est:
        print("  No existe un estudiante con ese ID.")
        return
    if input(f"  ¿Eliminar a {est['Nombre']} {est['Apellido']} y sus matrículas? (s/n): ").lower() == "s":
        EstudianteDAO.eliminar(id_est)
        print("  OK: estudiante eliminado.")


def crear_usuario():
    print("\n-- Crear usuario de la web (contraseña con hash) --")
    username = input("  Usuario: ").strip()
    password = input("  Contraseña: ").strip()
    rol = "ADMIN" if input("  ¿Es administrador? (s/n): ").lower() == "s" else "ESTUDIANTE"
    id_est = None if rol == "ADMIN" else pedir_entero("  ID del estudiante asociado: ")
    UsuarioDAO.crear(username, password, rol, id_est)
    print(f"  OK: usuario '{username}' creado como {rol}.")


def menu():
    opciones = {
        "1": ("Insertar estudiante", crear),
        "2": ("Consultar estudiantes", consultar),
        "3": ("Actualizar estudiante", actualizar),
        "4": ("Eliminar estudiante", eliminar),
        "5": ("Crear usuario de la web", crear_usuario),
    }
    while True:
        print("\n========= SISTEMA ACADÉMICO UMB – CRUD =========")
        for clave, (texto, _) in opciones.items():
            print(f"  {clave}. {texto}")
        print("  0. Salir")
        opcion = input("Seleccione una opción: ").strip()
        if opcion == "0":
            print("Hasta luego.")
            break
        if opcion not in opciones:
            print("  Opción no válida.")
            continue
        try:
            opciones[opcion][1]()
        except mysql.connector.IntegrityError as err:
            print(f"  ERROR de integridad (dato duplicado o referencia inválida): {err.msg}")
        except mysql.connector.Error as err:
            print(f"  ERROR de MySQL [{err.errno}]: {err.msg}")
        except ValueError as err:
            print(f"  Dato inválido: {err}")


if __name__ == "__main__":
    menu()
