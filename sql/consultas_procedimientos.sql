-- =====================================================================
-- consultas_procedimientos.sql
-- Consultas para revisar y probar los procedimientos almacenados,
-- funciones y triggers de universidad_umb en MySQL Workbench.
-- Ejecute cada bloque por separado (Ctrl + Enter sobre la línea, o
-- seleccione el bloque y Ctrl + Shift + Enter).
-- =====================================================================
USE universidad_umb;

-- ---------------------------------------------------------------------
-- A. ¿QUÉ PROCEDIMIENTOS, FUNCIONES Y TRIGGERS EXISTEN?
-- ---------------------------------------------------------------------

-- A1. Procedimientos almacenados de la base
SHOW PROCEDURE STATUS WHERE Db = 'universidad_umb';

-- A2. Funciones
SHOW FUNCTION STATUS WHERE Db = 'universidad_umb';

-- A3. Procedimientos y funciones con su tipo y fecha de creación
SELECT ROUTINE_NAME, ROUTINE_TYPE, DATA_TYPE AS retorna, SECURITY_TYPE, CREATED
FROM information_schema.ROUTINES
WHERE ROUTINE_SCHEMA = 'universidad_umb'
ORDER BY ROUTINE_TYPE, ROUTINE_NAME;

-- A4. Parámetros de cada procedimiento (IN / OUT y su tipo)
SELECT SPECIFIC_NAME AS rutina, ORDINAL_POSITION AS pos, PARAMETER_MODE AS modo,
       PARAMETER_NAME AS parametro, DTD_IDENTIFIER AS tipo
FROM information_schema.PARAMETERS
WHERE SPECIFIC_SCHEMA = 'universidad_umb' AND PARAMETER_MODE IS NOT NULL
ORDER BY SPECIFIC_NAME, ORDINAL_POSITION;

-- A5. Triggers: tabla, momento y evento
SELECT TRIGGER_NAME, EVENT_MANIPULATION AS evento, ACTION_TIMING AS momento,
       EVENT_OBJECT_TABLE AS tabla
FROM information_schema.TRIGGERS
WHERE TRIGGER_SCHEMA = 'universidad_umb';

-- A6. Ver el código de un procedimiento (cambie el nombre para ver otros)
SHOW CREATE PROCEDURE sp_registrar_matricula;
SHOW CREATE PROCEDURE sp_clasificar_estudiante;
SHOW CREATE PROCEDURE sp_actualizar_estados_curso;
SHOW CREATE PROCEDURE sp_resumen_curso;
SHOW CREATE TRIGGER trg_matricula_auditoria;


-- ---------------------------------------------------------------------
-- B. PROBAR CADA PROCEDIMIENTO (los OUT se leen con variables @)
-- ---------------------------------------------------------------------

-- B1. sp_registrar_matricula(IN estudiante, IN curso, OUT mensaje)
--     Matricula a Valentina (5) en Ingeniería de Software (4).
CALL sp_registrar_matricula(5, 4, @mensaje);
SELECT @mensaje AS mensaje;

--     Si se repite, el SP NO duplica: devuelve un mensaje de ERROR
CALL sp_registrar_matricula(5, 4, @mensaje);
SELECT @mensaje AS mensaje;

--     El trigger trg_matricula_auditoria dejó el rastro automáticamente
SELECT * FROM Auditoria_Matricula ORDER BY IdAuditoria DESC LIMIT 5;

-- B2. sp_clasificar_estudiante(IN estudiante, OUT promedio, OUT clasificación)
CALL sp_clasificar_estudiante(1, @promedio, @clasificacion);
SELECT @promedio AS promedio, @clasificacion AS clasificacion;

--     El SP también actualizó la tabla Estudiante
SELECT IdEstudiante, Nombre, Apellido, Promedio, EstadoAcademico
FROM Estudiante WHERE IdEstudiante = 1;

-- B3. sp_actualizar_estados_curso(IN curso, OUT procesados)  – usa un CURSOR
CALL sp_actualizar_estados_curso(1, @procesados);
SELECT @procesados AS matriculas_procesadas;

SELECT IdMatricula, IdEstudiante, NotaFinal, Estado
FROM Matricula WHERE IdCurso = 1;

-- B4. sp_resumen_curso(IN curso, OUT inscritos, OUT promedio, OUT aprobados)
--     Devuelve un result set (lista de estudiantes) Y tres parámetros OUT
CALL sp_resumen_curso(1, @inscritos, @prom_curso, @aprobados);
SELECT @inscritos AS inscritos, @prom_curso AS promedio, @aprobados AS aprobados;

-- B5. Recalcular a TODOS los estudiantes (lo mismo que el botón
--     "Recalcular promedios" de la web)
CALL sp_clasificar_estudiante(1, @p, @c);
CALL sp_clasificar_estudiante(2, @p, @c);
CALL sp_clasificar_estudiante(3, @p, @c);
CALL sp_clasificar_estudiante(4, @p, @c);
CALL sp_clasificar_estudiante(5, @p, @c);
SELECT IdEstudiante, CONCAT(Nombre, ' ', Apellido) AS estudiante, Promedio, EstadoAcademico
FROM Estudiante ORDER BY Promedio DESC;


-- ---------------------------------------------------------------------
-- C. FUNCIONES
-- ---------------------------------------------------------------------
SELECT IdEstudiante,
       fn_formatear_nombre(Nombre, Apellido) AS nombre_formateado,
       FechaNacimiento,
       fn_calcular_edad(FechaNacimiento)     AS edad
FROM Estudiante;


-- ---------------------------------------------------------------------
-- D. TRIGGERS DE VALIDACIÓN (deben FALLAR a propósito)
-- ---------------------------------------------------------------------
-- D1. Nota mayor a 5.0 -> Error 1644: La nota debe estar entre 0.0 y 5.0
UPDATE Matricula SET NotaFinal = 7.0 WHERE IdMatricula = 1;

-- D2. Nota negativa al insertar -> mismo error
INSERT INTO Matricula (IdEstudiante, IdCurso, FechaMatricula, NotaFinal)
VALUES (5, 3, CURDATE(), -1.0);


-- ---------------------------------------------------------------------
-- E. VER LO QUE INSERTÓ PYTHON (demo_insertar.py o la web)
-- ---------------------------------------------------------------------
-- E1. Últimos estudiantes creados
SELECT * FROM Estudiante ORDER BY IdEstudiante DESC LIMIT 5;

-- E2. Sus matrículas con el nombre del curso
SELECT m.IdMatricula, CONCAT(e.Nombre, ' ', e.Apellido) AS estudiante, c.Nombre AS curso,
       m.FechaMatricula, m.NotaFinal, m.Estado
FROM Matricula m
JOIN Estudiante e ON e.IdEstudiante = m.IdEstudiante
JOIN Curso c      ON c.IdCurso      = m.IdCurso
ORDER BY m.IdMatricula DESC LIMIT 10;

-- E3. Auditoría generada por el trigger (el Usuario muestra quién ejecutó)
SELECT * FROM Auditoria_Matricula ORDER BY IdAuditoria DESC LIMIT 10;

-- E4. Usuarios de la web (solo se guarda el hash de la contraseña)
SELECT IdUsuario, Username, Rol, IdEstudiante, Activo, LEFT(PasswordHash, 30) AS inicio_del_hash
FROM Usuario;
