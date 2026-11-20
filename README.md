# Práctica 8 – Conexión de aplicaciones a bases de datos

Universidad Manuela Beltrán · Teoría de Bases de Datos · Guía N.º 8
Python 3.12 + MySQL 8 (`universidad_umb`) + MongoDB (local o Atlas) + Flask.

## Estructura

```
sql/
  universidad_umb.sql          Base completa: tablas, datos, SP, funciones, triggers, usuario app_umb
  consultas_verificacion.sql   Consultas para comprobar que todo funciona
python/
  conexion.py                  Configuración (.env), pool de conexiones MySQL, conexión MongoDB
  dao.py                       Patrón DAO: Estudiante, Curso, Matricula, Usuario (MySQL) · Log, Preferencia, Perfil (MongoDB)
  actividad1_conexion.py       Act. 1 – conexión básica + SELECT + try/except
  actividad2_crud.py           Act. 2 – CRUD parametrizado con menú en consola
  actividad3_procedimientos.py Act. 3 – callproc() y parámetros OUT
  actividad4_mongodb.py        Act. 4 – CRUD con pymongo
  app.py + templates/          Act. 5 – aplicación web Flask con login (MySQL + MongoDB)
  demo_inyeccion.py            Demo: consulta concatenada vs parametrizada
```

## La aplicación web (Actividad 5)

Una sola web usa las dos bases de datos:

| Parte de la web | Base | Dónde se guarda / qué usa |
|---|---|---|
| Inicio de sesión, roles, cambio de contraseña, activar/desactivar cuentas | MySQL | tabla `Usuario` (contraseña con hash scrypt) |
| Estudiantes: buscar, crear, editar, eliminar, exportar CSV | MySQL | tabla `Estudiante`, función `fn_calcular_edad` |
| Matricular, poner nota, retirar | MySQL | `sp_registrar_matricula`, triggers de validación, `sp_actualizar_estados_curso` y `sp_clasificar_estudiante` (recalculan estado y promedio) |
| Cursos con estadísticas y detalle | MySQL | `LEFT JOIN + GROUP BY` y `sp_resumen_curso` (parámetros OUT + result set) |
| Auditoría de matrículas | MySQL | tabla `Auditoria_Matricula` (la llena el trigger) |
| Perfil del estudiante (intereses, semillero, GitHub) | MongoDB | colección `estudiantes_perfil` |
| Registro de actividad con filtros y totales por acción | MongoDB | colección `logs` (`find` + `aggregate`) |
| Bloqueo tras 5 intentos fallidos de login en 10 minutos | MongoDB | se cuentan los `LOGIN_FALLIDO` en `logs` |
| Preferencias (tema claro/oscuro) | MongoDB | colección `preferencias` |

Pantallas: **Panel** (cifras de las dos bases, estados académicos, acciones frecuentes, actividad reciente), **Estudiantes**, **ficha del estudiante** (une MySQL y MongoDB), **Cursos**, **Auditoría**, **Logs** y **Mi cuenta**. El estudiante solo ve su ficha y edita su propio perfil.

Seguridad: consultas parametrizadas, contraseñas con hash, token CSRF en todos los formularios, cookie de sesión `HttpOnly`/`SameSite`, control de rol por ruta y bloqueo por fuerza bruta. Si MongoDB se apaga, la parte académica (MySQL) sigue funcionando; si MySQL se apaga, la web muestra un aviso en vez de un error.

> Los datos de prueba se cargan con `Promedio = NULL` (para la Actividad 3). En el panel, el botón **Recalcular promedios** ejecuta los SP sobre toda la base.

## Manual de instalación

1. **Base de datos MySQL.** En MySQL Workbench abra `sql/universidad_umb.sql` y ejecútelo completo (⚡), o en consola:
   `mysql -u root -p < sql/universidad_umb.sql`.
   Crea la base, los datos de prueba, los SP de la Práctica 5 y el usuario `app_umb` (solo SELECT/INSERT/UPDATE/DELETE/EXECUTE).
2. **MongoDB.** Use el cluster de Atlas de la Práctica 6 (en *Network Access* permita su IP) o un MongoDB local.
3. **Dependencias Python.**
   ```
   cd python
   pip install -r requirements.txt
   ```
4. **Credenciales.** Copie `.env.example` como `.env` y ponga la contraseña de `app_umb` y su `MONGO_URI`.
5. **Ejecutar.**
   ```
   python actividad1_conexion.py
   python actividad2_crud.py
   python actividad3_procedimientos.py
   python actividad4_mongodb.py
   python app.py          # abrir http://127.0.0.1:5000
   ```
   Usuarios de prueba de la app: `admin / Admin2026*` (administrador) y `lgomez / Laura2026*` (estudiante).
6. **Verificar.** Ejecute `sql/consultas_verificacion.sql` en Workbench.

### Alternativa rápida con Docker

```
docker compose up -d      # MySQL 8 (carga sql/universidad_umb.sql) + MongoDB 7
```
Luego siga desde el paso 3.
