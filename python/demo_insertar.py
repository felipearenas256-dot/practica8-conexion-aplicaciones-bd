"""
demo_insertar.py – Inserta datos desde Python en las DOS bases para verlos
aparecer en MySQL Workbench (relacional) y en MongoDB Compass (no relacional).

  1. MySQL:   INSERT de un estudiante (consulta parametrizada)
  2. MySQL:   CALL sp_registrar_matricula      (SP con parámetro OUT)
  3. MySQL:   UPDATE de la nota -> trigger valida -> SP recalculan estado y promedio
  4. MySQL:   CALL sp_resumen_curso            (3 OUT + result set)
  5. MongoDB: insert/update del perfil del estudiante (colección estudiantes_perfil)
  6. MongoDB: insert_one en la colección logs

Ejecutar:  python demo_insertar.py
Cada ejecución crea un estudiante nuevo (el correo lleva la hora para no repetirse).
"""
from datetime import date, datetime

from conexion import base_mongo
from dao import CursoDAO, EstudianteDAO, LogDAO, MatriculaDAO, PerfilDAO

ID_CURSO = 1  # Teoría de Bases de Datos

marca = datetime.now().strftime("%H%M%S")
nombre, apellido = "Demo", f"Python {marca}"
email = f"demo.{marca}@umb.edu.co"

print("=" * 64)
print(" MySQL (relacional) – base universidad_umb")
print("=" * 64)

# 1. INSERT parametrizado
id_est = EstudianteDAO.insertar(nombre, apellido, date(2004, 6, 15), email)
print(f"1. INSERT INTO Estudiante ... VALUES (%s, %s, %s, %s)  ->  IdEstudiante = {id_est}")

# 2. Procedimiento almacenado con parámetro OUT
mensaje = MatriculaDAO.registrar(id_est, ID_CURSO)
print(f"2. CALL sp_registrar_matricula({id_est}, {ID_CURSO}, @msg)  ->  @msg = '{mensaje}'")

# 3. Nota: el trigger la valida y los SP recalculan estado y promedio
id_mat = MatriculaDAO.por_estudiante(id_est)[-1]["IdMatricula"]
MatriculaDAO.poner_nota(id_mat, 4.2)
est = EstudianteDAO.buscar_por_id(id_est)
print(f"3. UPDATE Matricula SET NotaFinal = 4.2 (matrícula {id_mat})")
print(f"   -> sp_clasificar_estudiante: Promedio = {est['Promedio']}, Estado = {est['EstadoAcademico']}")

# 4. SP con 3 parámetros OUT + result set
resumen, filas = CursoDAO.resumen(ID_CURSO)
print(f"4. CALL sp_resumen_curso({ID_CURSO}, @inscritos, @promedio, @aprobados)")
print(f"   -> inscritos = {resumen['inscritos']}, promedio = {resumen['promedio']}, aprobados = {resumen['aprobados']}")
print(f"   -> result set: {len(filas)} estudiantes en el curso")

print()
print("=" * 64)
print(" MongoDB (no relacional) – base universidad_umb_nosql")
print("=" * 64)

# 5. Documento del perfil (enlazado con MySQL por id_estudiante)
PerfilDAO.guardar(id_est, f"{nombre} {apellido}", ["bases de datos", "Python", "MongoDB"],
                  semillero="Semillero de Datos", github="demo-umb")
print(f"5. estudiantes_perfil.update_one({{id_estudiante: {id_est}}}, {{$set: ...}}, upsert=True)")
print("   ", PerfilDAO.obtener(id_est))

# 6. Log de la acción
LogDAO.registrar("demo_insertar.py", "DEMO_PYTHON", {"id_estudiante": id_est, "matricula": id_mat})
print(f"6. logs.insert_one({{usuario: 'demo_insertar.py', accion: 'DEMO_PYTHON', ...}})")
print(f"   total de logs en la colección: {base_mongo().logs.count_documents({})}")

print()
print("Verifíquelo:")
print(f"  Workbench: SELECT * FROM Estudiante WHERE IdEstudiante = {id_est};")
print(f"             SELECT * FROM Matricula WHERE IdEstudiante = {id_est};")
print("             SELECT * FROM Auditoria_Matricula ORDER BY IdAuditoria DESC;")
print(f"  Compass:   estudiantes_perfil -> filtro {{ id_estudiante: {id_est} }}")
print("             logs -> filtro { accion: 'DEMO_PYTHON' }")
print(f"  Web:       http://127.0.0.1:5000/estudiantes/{id_est}")
