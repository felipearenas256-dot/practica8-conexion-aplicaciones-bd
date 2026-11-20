"""
menu_cambios.py – Hacer cambios DESDE PYTHON y verlos en MySQL, MongoDB y la web.

Cada opción modifica las bases (con consultas parametrizadas a través de dao.py)
y dice exactamente dónde mirar el cambio:
  - Web:       se actualiza sola en ~3 s (indicador "En vivo")
  - Workbench: la consulta SELECT que se imprime
  - Compass:   el filtro que se imprime (pulsar Refresh)

Ejecutar:  python menu_cambios.py
"""
import warnings
from datetime import date

import mysql.connector

from dao import CursoDAO, EstudianteDAO, LogDAO, MatriculaDAO, PerfilDAO

warnings.filterwarnings("ignore", category=DeprecationWarning)
WEB = "http://127.0.0.1:5000"


def pedir(texto, defecto=""):
    valor = input(f"  {texto}{f' [{defecto}]' if defecto else ''}: ").strip()
    return valor or defecto


def pedir_id(texto="ID del estudiante"):
    try:
        return int(pedir(texto))
    except ValueError:
        print("  Debe ser un número.")
        return None


def log(accion, detalle):
    """Registra el cambio en la colección logs de MongoDB (aparece en Logs de la web)."""
    LogDAO.registrar("python", accion, detalle)


def donde_ver(id_est, mysql_sql=None, mongo=True):
    print("\n  Dónde verlo:")
    print(f"    Web:       {WEB}/estudiantes/{id_est}   (se actualiza sola)")
    if mysql_sql:
        print(f"    Workbench: {mysql_sql}")
    if mongo:
        print(f"    Compass:   estudiantes_perfil → filtro {{ id_estudiante: {id_est} }}  y  logs → {{ usuario: \"python\" }}")


def mostrar(id_est):
    """Muestra cómo está el estudiante en las DOS bases."""
    est = EstudianteDAO.buscar_por_id(id_est)
    if not est:
        print("  No existe en MySQL.")
        return False
    print(f"\n  MySQL   → {est['IdEstudiante']} · {est['Nombre']} {est['Apellido']} · {est['Email']} · "
          f"promedio {est['Promedio']} · {est['EstadoAcademico']}")
    for m in MatriculaDAO.por_estudiante(id_est):
        print(f"            matrícula {m['IdMatricula']}: {m['Curso']} · nota {m['NotaFinal']} · {m['Estado']}")
    perfil = PerfilDAO.obtener(id_est)
    print(f"  MongoDB → {perfil if perfil else '(sin perfil)'}")
    return True


# ------------------------------- Opciones -------------------------------
def crear():
    print("\n-- Crear estudiante (MySQL) + perfil (MongoDB) --")
    nombre, apellido = pedir("Nombre"), pedir("Apellido")
    fecha = pedir("Fecha de nacimiento AAAA-MM-DD", "2004-01-01")
    email = pedir("Email")
    intereses = [i.strip() for i in pedir("Intereses separados por coma", "bases de datos, Python").split(",") if i.strip()]
    id_est = EstudianteDAO.insertar(nombre, apellido, date.fromisoformat(fecha), email)    # MySQL INSERT
    PerfilDAO.guardar(id_est, f"{nombre} {apellido}", intereses)                         # MongoDB upsert
    log("CREAR_ESTUDIANTE", {"id": id_est, "email": email})
    print(f"  OK: estudiante {id_est} creado en MySQL y su perfil en MongoDB.")
    donde_ver(id_est, f"SELECT * FROM Estudiante WHERE IdEstudiante = {id_est};")


def cambiar_nombre():
    print("\n-- Cambiar nombre (MySQL) y actualizar el perfil (MongoDB) --")
    id_est = pedir_id()
    est = id_est and EstudianteDAO.buscar_por_id(id_est)
    if not est:
        print("  No existe ese estudiante.")
        return
    nombre = pedir("Nuevo nombre", est["Nombre"])
    apellido = pedir("Nuevo apellido", est["Apellido"])
    EstudianteDAO.actualizar(id_est, nombre, apellido, est["FechaNacimiento"], est["Email"])   # MySQL UPDATE
    perfil = PerfilDAO.obtener(id_est)
    PerfilDAO.guardar(id_est, f"{nombre} {apellido}", perfil.get("intereses", []),               # MongoDB $set
                      perfil.get("semillero"), (perfil.get("redes") or {}).get("github"))
    log("EDITAR_ESTUDIANTE", {"id": id_est, "nombre": f"{nombre} {apellido}"})
    print("  OK: nombre cambiado en MySQL y en el perfil de MongoDB.")
    donde_ver(id_est, f"SELECT Nombre, Apellido FROM Estudiante WHERE IdEstudiante = {id_est};")


def poner_nota():
    print("\n-- Poner nota (MySQL: trigger + procedimientos) --")
    id_est = pedir_id()
    if not id_est or not mostrar(id_est):
        return
    try:
        id_mat, nota = int(pedir("ID de la matrícula")), float(pedir("Nota (0.0 – 5.0)").replace(",", "."))
        if MatriculaDAO.poner_nota(id_mat, nota) == 0:
            print("  Esa matrícula no existe.")
            return
        log("PONER_NOTA", {"matricula": id_mat, "nota": nota})
        print(f"  OK: nota {nota} guardada. sp_actualizar_estados_curso y sp_clasificar_estudiante recalcularon estado y promedio.")
        mostrar(id_est)
        donde_ver(id_est, f"SELECT * FROM Matricula WHERE IdMatricula = {id_mat};", mongo=False)
    except mysql.connector.Error as err:
        print(f"  ERROR de MySQL (trigger): {err.msg}")
    except ValueError:
        print("  Datos inválidos.")


def matricular():
    print("\n-- Matricular (MySQL: sp_registrar_matricula) --")
    id_est = pedir_id()
    if not id_est:
        return
    for c in CursoDAO.listar():
        print(f"    {c['IdCurso']}. {c['Nombre']} ({c['Creditos']} cr.)")
    id_curso = pedir_id("ID del curso")
    if not id_curso:
        return
    mensaje = MatriculaDAO.registrar(id_est, id_curso)   # CALL sp_registrar_matricula(..., @mensaje)
    log("MATRICULAR", {"id_estudiante": id_est, "id_curso": id_curso, "mensaje": mensaje})
    print(f"  OUT p_mensaje = {mensaje}")
    donde_ver(id_est, "SELECT * FROM Auditoria_Matricula ORDER BY IdAuditoria DESC;", mongo=False)


def editar_perfil():
    print("\n-- Editar perfil (MongoDB) --")
    id_est = pedir_id()
    est = id_est and EstudianteDAO.buscar_por_id(id_est)
    if not est:
        print("  No existe ese estudiante en MySQL.")
        return
    perfil = PerfilDAO.obtener(id_est)
    intereses = pedir("Intereses separados por coma", ", ".join(perfil.get("intereses", [])))
    semillero = pedir("Semillero (vacío = sin semillero)", perfil.get("semillero", ""))
    github = pedir("Usuario de GitHub (vacío = sin GitHub)", (perfil.get("redes") or {}).get("github", ""))
    PerfilDAO.guardar(id_est, f"{est['Nombre']} {est['Apellido']}",
                      [i.strip() for i in intereses.split(",") if i.strip()], semillero or None, github or None)
    log("EDITAR_PERFIL", {"id_estudiante": id_est})
    print("  OK: perfil guardado en MongoDB.")
    print(f"  {PerfilDAO.obtener(id_est)}")
    donde_ver(id_est)


def eliminar():
    print("\n-- Eliminar estudiante (MySQL + MongoDB) --")
    id_est = pedir_id()
    if not id_est or not mostrar(id_est):
        return
    if pedir("¿Seguro? (s/n)", "n").lower() != "s":
        print("  Cancelado.")
        return
    EstudianteDAO.eliminar(id_est)   # MySQL: DELETE de matrículas y estudiante en una transacción
    PerfilDAO.eliminar(id_est)       # MongoDB: delete_one del perfil
    log("ELIMINAR_ESTUDIANTE", {"id": id_est})
    print(f"  OK: estudiante {id_est} eliminado de MySQL y su perfil de MongoDB.")
    print(f"  Web: {WEB}/estudiantes ya no lo muestra.")


def ver():
    print("\n-- Ver un estudiante en las dos bases --")
    id_est = pedir_id()
    if id_est:
        mostrar(id_est)


def listar():
    print()
    for e in EstudianteDAO.listar():
        print(f"  {e['IdEstudiante']:<4}{e['Nombre'][:14]:<15}{e['Apellido'][:14]:<15}{e['EstadoAcademico']}")


OPCIONES = {
    "1": ("Listar estudiantes (MySQL)", listar),
    "2": ("Ver un estudiante en MySQL y MongoDB", ver),
    "3": ("Crear estudiante (MySQL) + perfil (MongoDB)", crear),
    "4": ("Cambiar nombre (MySQL + MongoDB)", cambiar_nombre),
    "5": ("Poner nota (MySQL, trigger y procedimientos)", poner_nota),
    "6": ("Matricular (procedimiento sp_registrar_matricula)", matricular),
    "7": ("Editar perfil (MongoDB)", editar_perfil),
    "8": ("Eliminar estudiante (MySQL + MongoDB)", eliminar),
}

if __name__ == "__main__":
    while True:
        print("\n========== PRÁCTICA 8 – CAMBIOS DESDE PYTHON ==========")
        print("  Cada cambio se guarda en MySQL / MongoDB y la web lo muestra sola.")
        for k, (texto, _) in OPCIONES.items():
            print(f"  {k}. {texto}")
        print("  0. Salir")
        op = input("Opción: ").strip()
        if op == "0":
            break
        if op not in OPCIONES:
            print("  Opción no válida.")
            continue
        try:
            OPCIONES[op][1]()
        except mysql.connector.IntegrityError as err:
            print(f"  ERROR de integridad en MySQL: {err.msg}")
        except mysql.connector.Error as err:
            print(f"  ERROR de MySQL [{err.errno}]: {err.msg}")
        except Exception as err:
            print(f"  ERROR: {err}")
