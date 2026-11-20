-- =====================================================================
-- PRÁCTICA 8 – CONSULTAS DE VERIFICACIÓN
-- Ejecutar en MySQL Workbench DESPUÉS de universidad_umb.sql y después
-- de correr cada script de Python, para comprobar que los cambios hechos
-- desde la web y Python quedaron en la base de datos.
-- =====================================================================
USE universidad_umb;

-- V1. La base tiene las 5 tablas esperadas
SELECT TABLE_NAME, TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'universidad_umb'
ORDER BY TABLE_NAME;

-- V2. Los procedimientos, funciones y triggers existen
SELECT ROUTINE_TYPE, ROUTINE_NAME
FROM information_schema.ROUTINES
WHERE ROUTINE_SCHEMA = 'universidad_umb'
ORDER BY ROUTINE_TYPE, ROUTINE_NAME;

SELECT TRIGGER_NAME, ACTION_TIMING, EVENT_MANIPULATION, EVENT_OBJECT_TABLE
FROM information_schema.TRIGGERS
WHERE TRIGGER_SCHEMA = 'universidad_umb';

-- V3. El usuario de la aplicación existe y SOLO tiene privilegios DML + EXECUTE
SHOW GRANTS FOR 'app_umb'@'%';

-- V4. Conteo de registros (antes y después del CRUD de la Actividad 2)
SELECT (SELECT COUNT(*) FROM Estudiante) AS estudiantes,
       (SELECT COUNT(*) FROM Curso)      AS cursos,
       (SELECT COUNT(*) FROM Matricula)  AS matriculas,
       (SELECT COUNT(*) FROM Usuario)    AS usuarios,
       (SELECT COUNT(*) FROM Auditoria_Matricula) AS auditorias;

-- V5. Listado de estudiantes (debe coincidir con la salida de actividad1_conexion.py)
SELECT IdEstudiante, Nombre, Apellido, Email, Promedio, EstadoAcademico
FROM Estudiante ORDER BY IdEstudiante;

-- V6. Matrículas con nombre de estudiante y curso
SELECT m.IdMatricula, fn_formatear_nombre(e.Nombre, e.Apellido) AS Estudiante,
       c.Nombre AS Curso, m.NotaFinal, m.Estado, m.FechaMatricula
FROM Matricula m
JOIN Estudiante e ON e.IdEstudiante = m.IdEstudiante
JOIN Curso c      ON c.IdCurso      = m.IdCurso
ORDER BY m.IdMatricula;

-- V7. Resultado de la Actividad 3: promedio y clasificación que dejó
--     sp_clasificar_estudiante (antes de correrla, Promedio = NULL)
SELECT IdEstudiante, CONCAT(Nombre, ' ', Apellido) AS Estudiante, Promedio, EstadoAcademico
FROM Estudiante ORDER BY Promedio DESC;

-- V8. Resultado de la Actividad 3: estados del curso 1 tras sp_actualizar_estados_curso
SELECT Estado, COUNT(*) AS cantidad FROM Matricula WHERE IdCurso = 1 GROUP BY Estado;

-- V9. Matrículas registradas desde Python con el SP quedan auditadas por el trigger
SELECT a.IdAuditoria, a.IdMatricula, a.IdEstudiante, a.IdCurso, a.Accion, a.Usuario, a.FechaHora
FROM Auditoria_Matricula a ORDER BY a.IdAuditoria;

-- V10. Contraseñas: se guarda el HASH, nunca el texto plano
SELECT Username, Rol, LEFT(PasswordHash, 30) AS inicio_hash, LENGTH(PasswordHash) AS largo_hash
FROM Usuario;

-- V11. Llamada manual a los SP (mismo resultado que desde Python)
CALL sp_registrar_matricula(3, 4, @msg);           SELECT @msg AS mensaje;
CALL sp_clasificar_estudiante(1, @prom, @clas);    SELECT @prom AS promedio, @clas AS clasificacion;
CALL sp_actualizar_estados_curso(2, @n);           SELECT @n AS procesados;
CALL sp_resumen_curso(1, @ins, @p, @apr);          SELECT @ins AS inscritos, @p AS promedio, @apr AS aprobados;

-- V12. Prueba de inyección SQL: la cadena maliciosa se trata como TEXTO.
--      Una consulta parametrizada con ese valor no devuelve filas.
SET @entrada = '1 OR 1=1';
PREPARE stmt FROM 'SELECT IdEstudiante, Nombre FROM Estudiante WHERE IdEstudiante = ?';
EXECUTE stmt USING @entrada;     -- 1 fila como mucho (convierte '1 OR 1=1' a 1), nunca todas
DEALLOCATE PREPARE stmt;

SET @entrada = 'x'' OR ''1''=''1';
PREPARE stmt FROM 'SELECT IdEstudiante, Nombre FROM Estudiante WHERE Apellido = ?';
EXECUTE stmt USING @entrada;     -- 0 filas: la comilla no rompe la consulta
DEALLOCATE PREPARE stmt;

-- V13. El trigger sigue protegiendo los datos aunque la orden venga de la web
-- (debe fallar con ERROR 1644: La nota debe estar entre 0.0 y 5.0)
-- UPDATE Matricula SET NotaFinal = 7.0 WHERE IdMatricula = 1;
