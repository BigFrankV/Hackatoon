# Credenciales de desarrollo local

Este documento explica dónde encontrar cada acceso, pero no contiene contraseñas. Los valores reales se guardan en el `.env` raíz, que está ignorado por Git. No copies sus contraseñas a este documento, al repositorio ni a capturas compartidas.

## Preparar un clon nuevo

1. Clona el repositorio y ejecuta `.\scripts\dev-up.ps1` desde la raíz.
2. En la primera ejecución se crean los `.env` locales desde las plantillas. Completa `BOOTSTRAP_SUPERADMIN_EMAIL` y `BOOTSTRAP_SUPERADMIN_PASSWORD`; sustituye también los passwords de ejemplo de `POSTGRES_PASSWORD` y `PGADMIN_DEFAULT_PASSWORD`.
3. Ejecuta el script otra vez. Si las variables `DEV_SEED_*_PASSWORD` están vacías, el script las genera aleatoriamente y las guarda en el `.env` local.

Los nombres, correos y roles demo son iguales en cada clon; cada computadora mantiene sus propias contraseñas. No envíes el archivo `.env` a GitHub ni por chat: comparte el repositorio y las plantillas, no los secretos locales.

## PostgreSQL

- Desde el equipo: host `localhost`, puerto `5432`.
- Desde otro contenedor Compose: host `db`, puerto `5432`.
- Base de datos y usuario actuales: `licitaciones` (variables `POSTGRES_DB` y `POSTGRES_USER`).
- Contraseña: `POSTGRES_PASSWORD`.

## pgAdmin

- Dirección: `http://localhost:5050`.
- Usuario/correo actual: `pgadmin@hackatoon.dev` (`PGADMIN_DEFAULT_EMAIL`).
- Contraseña: `PGADMIN_DEFAULT_PASSWORD`.
- El script genera la configuración local de pgAdmin usando `POSTGRES_DB` y `POSTGRES_USER`; el servidor `Licitaciones local` se registra automáticamente y se sincroniza al iniciar. Usa host `db`, puerto `5432`; si pgAdmin pide la contraseña de PostgreSQL, usa `POSTGRES_PASSWORD`.

pgAdmin conserva su configuración en un volumen. Cambiar `PGADMIN_DEFAULT_PASSWORD` en `.env` no cambia la contraseña de un usuario ya creado mientras ese volumen se conserve.

`SECRET_KEY` en `backend/.env.example` es solo para desarrollo. Usa una clave propia y un gestor de secretos para cualquier despliegue real.

## Primer superadministrador

- Dirección de la aplicación: `http://localhost:5173` si se inicia el frontend en Docker; si no, inicia Vite desde `frontend/`.
- Correo actual: `admin@hackatoon.dev` (`BOOTSTRAP_SUPERADMIN_EMAIL`).
- Contraseña inicial: `BOOTSTRAP_SUPERADMIN_PASSWORD`.

El bootstrap crea la cuenta solo si la base no tiene ya un `super_admin`. La cuenta inicial exige cambiar la contraseña al iniciar sesión. Después de cambiarla en la aplicación, la nueva contraseña no se escribe de vuelta en `.env`; la variable solo conserva la contraseña inicial. Cambiar las variables de bootstrap no modifica una cuenta existente.

## Empresas y usuarios demo

El arranque local crea dos empresas estables para desarrollo:

| Empresa | Admin | Usuario normal |
|---|---|---|
| Demo Norte | `admin.norte@hackatoon.dev` | `usuario.norte@hackatoon.dev` |
| Demo Sur | `admin.sur@hackatoon.dev` | `usuario.sur@hackatoon.dev` |

Sus datos, correos y roles son iguales en cada clon. Cada computadora genera contraseñas distintas y las guarda solo en `.env`: `DEV_SEED_NORTH_ADMIN_PASSWORD`, `DEV_SEED_NORTH_USER_PASSWORD`, `DEV_SEED_SOUTH_ADMIN_PASSWORD` y `DEV_SEED_SOUTH_USER_PASSWORD`. Las cuentas demo también exigen cambio de contraseña al primer inicio.

El seeder es idempotente: crea registros faltantes y no reemplaza contraseñas ni modifica usuarios que ya existan. Se ejecuta solo con el perfil local `dev`; no forma parte de las migraciones de esquema.

## Cambios y reinicios

Los servicios se pueden detener sin borrar la base ni los accesos guardados:

```powershell
docker compose --profile dev --profile frontend down
```

No uses `down --volumes` salvo que quieras eliminar permanentemente los datos locales de PostgreSQL y pgAdmin. Además, cambiar `POSTGRES_PASSWORD` en `.env` no cambia por sí solo la contraseña del usuario dentro de una base ya inicializada.
