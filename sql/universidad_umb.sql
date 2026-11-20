-- =====================================================================
-- PRÁCTICA 8 – CONEXIÓN DE APLICACIONES A BASES DE DATOS
-- Universidad Manuela Beltrán · Teoría de Bases de Datos · Guía N.º 8
-- SGBD: MySQL 8.x
--
-- Script completo de la base universidad_umb (Prácticas 1-5) + lo nuevo
-- de la Práctica 8:
--   1. Esquema: Estudiante, Curso, Matricula, Auditoria_Matricula
--   2. NUEVO: tabla Usuario (login de la web, contraseñas hash)
--   3. Datos de prueba
--   4. Procedimientos almacenados de la Práctica 5 (con parámetros OUT)
--   5. Funciones y triggers de la Práctica 5
--   6. Usuario de aplicación con privilegios mínimos (Práctica 4)
--
-- Ejecución: MySQL Workbench -> File > Run SQL Script, o en consola:
--   mysql -u root -p < universidad_umb.sql
-- =====================================================================

SET NAMES utf8mb4;
DROP DATABASE IF EXISTS universidad_umb;
CREATE DATABASE universidad_umb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE universidad_umb;

-- ---------------------------------------------------------------------
-- 1. ESQUEMA BASE (Prácticas 1-5)
-- ---------------------------------------------------------------------
CREATE TABLE Estudiante (
    IdEstudiante      INT AUTO_INCREMENT PRIMARY KEY,
    Nombre            VARCHAR(50)  NOT NULL,
    Apellido          VARCHAR(50)  NOT NULL,
    FechaNacimiento   DATE         NOT NULL,
    Email             VARCHAR(100) UNIQUE,
    Promedio          DECIMAL(3,2) NULL,
    EstadoAcademico   VARCHAR(15)  NOT NULL DEFAULT 'SIN NOTAS'
);

CREATE TABLE Curso (
    IdCurso   INT AUTO_INCREMENT PRIMARY KEY,
    Nombre    VARCHAR(80) NOT NULL,
    Creditos  TINYINT     NOT NULL
);

CREATE TABLE Matricula (
    IdMatricula      INT AUTO_INCREMENT PRIMARY KEY,
    IdEstudiante     INT          NOT NULL,
    IdCurso          INT          NOT NULL,
    FechaMatricula   DATE         NOT NULL,
    NotaFinal        DECIMAL(2,1) NULL,
    Estado           VARCHAR(12)  NOT NULL DEFAULT 'EN CURSO',
    CONSTRAINT uq_est_curso UNIQUE (IdEstudiante, IdCurso),
    CONSTRAINT fk_mat_est   FOREIGN KEY (IdEstudiante) REFERENCES Estudiante(IdEstudiante),
    CONSTRAINT fk_mat_curso FOREIGN KEY (IdCurso)      REFERENCES Curso(IdCurso)
);

-- Auditoría de matrículas (la llena el trigger AFTER INSERT)
CREATE TABLE Auditoria_Matricula (
    IdAuditoria    INT AUTO_INCREMENT PRIMARY KEY,
    IdMatricula    INT          NOT NULL,
    IdEstudiante   INT          NOT NULL,
    IdCurso        INT          NOT NULL,
    Accion         VARCHAR(10)  NOT NULL,
    Usuario        VARCHAR(100) NOT NULL,
    FechaHora      DATETIME     NOT NULL
);

-- ---------------------------------------------------------------------
-- 2. NUEVO EN LA PRÁCTICA 8: usuarios de la web (Actividad 5)
--    La contraseña NUNCA se guarda en texto plano: se guarda el hash
--    generado en Python con werkzeug.security.generate_password_hash
--    (algoritmo scrypt + sal aleatoria).
-- ---------------------------------------------------------------------
CREATE TABLE Usuario (
    IdUsuario       INT AUTO_INCREMENT PRIMARY KEY,
    Username        VARCHAR(30)  NOT NULL UNIQUE,
    PasswordHash    VARCHAR(255) NOT NULL,
    Rol             ENUM('ADMIN','ESTUDIANTE') NOT NULL DEFAULT 'ESTUDIANTE',
    IdEstudiante    INT          NULL,              -- solo para rol ESTUDIANTE
    Activo          BOOLEAN      NOT NULL DEFAULT TRUE,
    FechaCreacion   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_usu_est FOREIGN KEY (IdEstudiante) REFERENCES Estudiante(IdEstudiante)
        ON DELETE SET NULL
);

-- ---------------------------------------------------------------------
-- 3. DATOS DE PRUEBA
-- ---------------------------------------------------------------------
INSERT INTO Estudiante (Nombre, Apellido, FechaNacimiento, Email) VALUES
 ('Laura',    'Gómez',     '2003-05-14', 'laura.gomez@umb.edu.co'),
 ('Andrés',   'Rodríguez', '2002-11-02', 'andres.rodriguez@umb.edu.co'),
 ('Camila',   'Torres',    '2004-01-23', 'camila.torres@umb.edu.co'),
 ('Julián',   'Martínez',  '2001-08-30', 'julian.martinez@umb.edu.co'),
 ('Valentina','Ruiz',      '2005-03-09', 'valentina.ruiz@umb.edu.co');

INSERT INTO Curso (Nombre, Creditos) VALUES
 ('Teoría de Bases de Datos', 3),
 ('Programación Orientada a Objetos', 3),
 ('Estructuras de Datos', 4),
 ('Ingeniería de Software', 3);

INSERT INTO Matricula (IdEstudiante, IdCurso, FechaMatricula, NotaFinal) VALUES
 (1, 1, '2026-07-28', 4.8), (1, 2, '2026-07-28', 4.4), (1, 3, '2026-07-28', 4.6),
 (2, 1, '2026-07-28', 4.2), (2, 2, '2026-07-28', 3.9), (2, 3, '2026-07-28', 4.1),
 (3, 1, '2026-07-28', 3.2), (3, 2, '2026-07-28', 3.5), (3, 3, '2026-07-28', 2.9),
 (4, 1, '2026-07-28', 2.1), (4, 2, '2026-07-28', 2.8), (4, 3, '2026-07-28', 3.0),
 (5, 1, '2026-07-28', NULL);

-- Usuarios de la web (hash scrypt, NO contraseñas en claro).
--   admin  -> contraseña de prueba: Admin2026*
--   lgomez -> contraseña de prueba: Laura2026*
-- Para crear usuarios nuevos use la opción "Crear usuario" de actividad2_crud.py.
INSERT INTO Usuario (Username, PasswordHash, Rol, IdEstudiante) VALUES
 ('admin',  'scrypt:32768:8:1$nXuqUmJLoIk9YejA$dca0ca59e979a3512f1b7c47389071ad435dfc450bcfe677844c9b2069fc5562d6f927eba75cafb9d0c3d3c5c765c77edb16c8178fbaaafe919c13edc8b41b3d', 'ADMIN', NULL),
 ('lgomez', 'scrypt:32768:8:1$tXO4UDdiNgoWL7jp$601b5cab25a950dfcc179ca37b4274674a8db075a868b77884b9df3208bbdf3de7ffbbfc48a2d8b304e4f7d6e8ce5efade0cb55b4c01ad20ec6101f073e2e80a', 'ESTUDIANTE', 1);

-- ---------------------------------------------------------------------
-- 4. PROCEDIMIENTOS ALMACENADOS (Práctica 5) – se llaman desde Python
--    en la Actividad 3 con cursor.callproc()
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_registrar_matricula;
DROP PROCEDURE IF EXISTS sp_clasificar_estudiante;
DROP PROCEDURE IF EXISTS sp_actualizar_estados_curso;
DROP PROCEDURE IF EXISTS sp_resumen_curso;

DELIMITER //

-- Registra una matrícula validando estudiante, curso y duplicados.
-- OUT p_mensaje: 'OK: ...' o 'ERROR: ...'
CREATE PROCEDURE sp_registrar_matricula(
    IN  p_id_estudiante INT,
    IN  p_id_curso      INT,
    OUT p_mensaje       VARCHAR(150)
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_mensaje = 'ERROR: no se pudo registrar la matrícula (error SQL).';
    END;

    IF NOT EXISTS (SELECT 1 FROM Estudiante WHERE IdEstudiante = p_id_estudiante) THEN
        SET p_mensaje = CONCAT('ERROR: el estudiante ', p_id_estudiante, ' no existe.');
    ELSEIF NOT EXISTS (SELECT 1 FROM Curso WHERE IdCurso = p_id_curso) THEN
        SET p_mensaje = CONCAT('ERROR: el curso ', p_id_curso, ' no existe.');
    ELSEIF EXISTS (SELECT 1 FROM Matricula
                   WHERE IdEstudiante = p_id_estudiante AND IdCurso = p_id_curso) THEN
        SET p_mensaje = 'ERROR: el estudiante ya está matriculado en ese curso.';
    ELSE
        START TRANSACTION;
        INSERT INTO Matricula (IdEstudiante, IdCurso, FechaMatricula)
        VALUES (p_id_estudiante, p_id_curso, CURDATE());
        COMMIT;
        SET p_mensaje = CONCAT('OK: matrícula ', LAST_INSERT_ID(), ' registrada el ', CURDATE(), '.');
    END IF;
END //

-- Calcula el promedio del estudiante, lo clasifica y actualiza su estado.
-- OUT p_promedio, OUT p_clasificacion
CREATE PROCEDURE sp_clasificar_estudiante(
    IN  p_id_estudiante INT,
    OUT p_promedio      DECIMAL(3,2),
    OUT p_clasificacion VARCHAR(15)
)
BEGIN
    IF NOT EXISTS (SELECT 1 FROM Estudiante WHERE IdEstudiante = p_id_estudiante) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El estudiante no existe.';
    END IF;

    SELECT ROUND(AVG(NotaFinal), 2) INTO p_promedio
    FROM Matricula
    WHERE IdEstudiante = p_id_estudiante AND NotaFinal IS NOT NULL;

    SET p_clasificacion = CASE
        WHEN p_promedio IS NULL THEN 'SIN NOTAS'
        WHEN p_promedio >= 4.5  THEN 'EXCELENTE'
        WHEN p_promedio >= 4.0  THEN 'BUENO'
        WHEN p_promedio >= 3.0  THEN 'APROBADO'
        ELSE 'REPROBADO'
    END;

    UPDATE Estudiante
    SET Promedio = p_promedio, EstadoAcademico = p_clasificacion
    WHERE IdEstudiante = p_id_estudiante;
END //

-- Recorre con un cursor las matrículas de un curso y actualiza su estado.
-- OUT p_procesados: número de matrículas actualizadas
CREATE PROCEDURE sp_actualizar_estados_curso(
    IN  p_id_curso     INT,
    OUT p_procesados   INT
)
BEGIN
    DECLARE v_fin          BOOLEAN DEFAULT FALSE;
    DECLARE v_id_matricula INT;
    DECLARE v_nota         DECIMAL(2,1);
    DECLARE v_estado       VARCHAR(12);

    DECLARE cur_matriculas CURSOR FOR
        SELECT IdMatricula, NotaFinal FROM Matricula WHERE IdCurso = p_id_curso;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_fin = TRUE;

    SET p_procesados = 0;
    OPEN cur_matriculas;
    recorrido: LOOP
        FETCH cur_matriculas INTO v_id_matricula, v_nota;
        IF v_fin THEN
            LEAVE recorrido;
        END IF;
        SET v_estado = CASE
            WHEN v_nota IS NULL THEN 'EN CURSO'
            WHEN v_nota >= 3.0  THEN 'APROBADO'
            ELSE 'REPROBADO'
        END;
        UPDATE Matricula SET Estado = v_estado WHERE IdMatricula = v_id_matricula;
        SET p_procesados = p_procesados + 1;
    END LOOP recorrido;
    CLOSE cur_matriculas;
END //

-- NUEVO (Práctica 8): SP que devuelve un result set + parámetros OUT,
-- para mostrar en Python cómo leer ambos con callproc() + stored_results().
CREATE PROCEDURE sp_resumen_curso(
    IN  p_id_curso      INT,
    OUT p_inscritos     INT,
    OUT p_promedio      DECIMAL(3,2),
    OUT p_aprobados     INT
)
BEGIN
    SELECT COUNT(*), ROUND(AVG(NotaFinal), 2), SUM(NotaFinal >= 3.0)
      INTO p_inscritos, p_promedio, p_aprobados
    FROM Matricula WHERE IdCurso = p_id_curso;

    -- Result set: listado de estudiantes del curso
    SELECT e.IdEstudiante, CONCAT(e.Nombre, ' ', e.Apellido) AS Estudiante,
           m.NotaFinal, m.Estado
    FROM Matricula m JOIN Estudiante e ON e.IdEstudiante = m.IdEstudiante
    WHERE m.IdCurso = p_id_curso
    ORDER BY m.NotaFinal DESC;
END //

DELIMITER ;

-- ---------------------------------------------------------------------
-- 5. FUNCIONES Y TRIGGERS (Práctica 5)
-- ---------------------------------------------------------------------
DROP FUNCTION IF EXISTS fn_calcular_edad;
DROP FUNCTION IF EXISTS fn_formatear_nombre;
DROP TRIGGER IF EXISTS trg_matricula_valida_nota;
DROP TRIGGER IF EXISTS trg_matricula_valida_nota_upd;
DROP TRIGGER IF EXISTS trg_matricula_auditoria;

DELIMITER //
CREATE FUNCTION fn_calcular_edad(p_fecha_nac DATE)
RETURNS INT NOT DETERMINISTIC NO SQL
BEGIN
    IF p_fecha_nac IS NULL THEN RETURN NULL; END IF;
    RETURN TIMESTAMPDIFF(YEAR, p_fecha_nac, CURDATE());
END //

CREATE FUNCTION fn_formatear_nombre(p_nombre VARCHAR(50), p_apellido VARCHAR(50))
RETURNS VARCHAR(105) DETERMINISTIC NO SQL
BEGIN
    RETURN CONCAT(UPPER(TRIM(p_apellido)), ', ', UPPER(TRIM(p_nombre)));
END //

-- Rechaza notas fuera de 0.0 – 5.0 al insertar
CREATE TRIGGER trg_matricula_valida_nota
BEFORE INSERT ON Matricula FOR EACH ROW
BEGIN
    IF NEW.NotaFinal IS NOT NULL AND (NEW.NotaFinal < 0 OR NEW.NotaFinal > 5.0) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La nota debe estar entre 0.0 y 5.0';
    END IF;
END //

-- Misma validación al actualizar
CREATE TRIGGER trg_matricula_valida_nota_upd
BEFORE UPDATE ON Matricula FOR EACH ROW
BEGIN
    IF NEW.NotaFinal IS NOT NULL AND (NEW.NotaFinal < 0 OR NEW.NotaFinal > 5.0) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La nota debe estar entre 0.0 y 5.0';
    END IF;
END //

-- Deja rastro de cada matrícula nueva
CREATE TRIGGER trg_matricula_auditoria
AFTER INSERT ON Matricula FOR EACH ROW
BEGIN
    INSERT INTO Auditoria_Matricula (IdMatricula, IdEstudiante, IdCurso, Accion, Usuario, FechaHora)
    VALUES (NEW.IdMatricula, NEW.IdEstudiante, NEW.IdCurso, 'INSERT', CURRENT_USER(), NOW());
END //
DELIMITER ;

-- ---------------------------------------------------------------------
-- 6. USUARIO DE APLICACIÓN CON PRIVILEGIOS MÍNIMOS (Práctica 4)
--    Las aplicaciones Python se conectan con este usuario, NO con root.
--    Solo puede leer/escribir datos y ejecutar SP; no puede crear ni
--    borrar tablas (DROP, ALTER, GRANT quedan denegados).
--    IMPORTANTE: cambie la contraseña antes de usarlo y guárdela solo en
--    el archivo .env de la aplicación (nunca en el código fuente).
-- ---------------------------------------------------------------------
DROP USER IF EXISTS 'app_umb'@'%';
CREATE USER 'app_umb'@'%' IDENTIFIED BY 'CambiarEstaClave_2026';
GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE ON universidad_umb.* TO 'app_umb'@'%';
FLUSH PRIVILEGES;

-- Comprobación rápida
SELECT 'Base universidad_umb creada correctamente' AS resultado;
SHOW TABLES;
