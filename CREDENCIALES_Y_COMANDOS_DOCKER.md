# Credenciales y comandos Docker — Licitaciones AI

> Guía para entorno de desarrollo/local. No usar estas credenciales en producción.

## 1. Credenciales y URLs

### 1.1 Base de datos PostgreSQL (Docker Compose)

| Campo | Valor |
|---|---|
| Host (desde tu máquina) | `localhost` |
| Host (desde contenedores en red `hackatoon_default`) | `licitaciones-db` / `db` |
| Puerto | `5432` |
| Base de datos | `licitaciones` |
| Usuario | `licitaciones` |
| Contraseña | `licitaciones_dev_password` |
| URL (host) | `postgresql://licitaciones:licitaciones_dev_password@localhost:5432/licitaciones` |
| URL async (backend) | `postgresql+asyncpg://licitaciones:licitaciones_dev_password@localhost:5432/licitaciones` |

Fuente: `docker-compose.yml` (servicio `db`, con valores por defecto) y `backend/.env.example`.

### 1.2 Backend (API)

| Campo | Valor |
|---|---|
| URL base API | `http://localhost:8000/api/v1` |
| Healthcheck | `http://localhost:8000/api/v1/health` |
| Swagger / Docs | `http://localhost:8000/docs` |
| OpenAPI JSON | `http://localhost:8000/openapi.json` |
| `SECRET_KEY` (dev) | `change-me-in-development-only` |
| `JWT_ALGORITHM` | `HS256` |
| Access token expira | `15` minutos |
| Refresh token expira | `7` días |
| CORS origen dev | `http://localhost:5173` |

Fuente: `backend/.env.example`. En Docker Compose, el backend recibe `DATABASE_URL` apuntando a `db:5432`.

### 1.3 Frontend

| Campo | Valor |
|---|---|
| URL local (manual o Docker) | `http://localhost:5173` |
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` |
| `VITE_APP_NAME` | `Licitaciones AI` |

Fuente: `frontend/.env.example`.

### 1.4 Usuario inicial de la aplicación (bootstrap)

La migración crea tablas, pero **no crea usuarios**. El primer `super_admin` se crea una vez manualmente.

Ejemplo usado en entorno local:

| Campo | Valor |
|---|---|
| Email | `superadmin@local.dev` |
| Contraseña | `ChangeMe123!Strong` |
| Rol | `super_admin` |
| `must_change_password` | `true` (pedirá cambio al iniciar sesión) |

> Si el usuario ya existe, no volver a crearlo. Cambiar la contraseña después del primer login.

### 1.5 pgAdmin (opcional, no incluido en docker-compose)

Si se levanta el contenedor opcional de pgAdmin:

| Campo | Valor |
|---|---|
| URL pgAdmin | `http://localhost:5050` |
| Email pgAdmin | `admin@local.dev` |
| Contraseña pgAdmin | `admin` |

Al registrar el servidor dentro de pgAdmin:

| Campo | Valor |
|---|---|
| Host name/address | `licitaciones-db` |
| Port | `5432` |
| Maintenance database | `licitaciones` |
| Username | `licitaciones` |
| Password | `licitaciones_dev_password` |

## 2. Comandos para un compañero que clona el repo (primera vez)

### 2.1 Prerrequisitos

- Git
- Docker Desktop / Docker Engine + Docker Compose
- Node.js 22+ y npm (para correr frontend manual)

### 2.2 Clonar y preparar entorno

```powershell
git clone <URL_DEL_REPOSITORIO>
cd <CARPETA_DEL_REPOSITORIO>
```

Opcional: copiar envs (Docker Compose ya usa `.env.example` por defecto, pero es útil para desarrollo manual):

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env
```

### 2.3 Crear imágenes y levantar contenedores (recomendado: sin frontend en Docker)

Levanta DB, backend y worker, construyendo imágenes si no existen:

```powershell
docker compose up --build -d db backend worker
```

Verificar estado:

```powershell
docker compose ps -a
```

### 2.4 Ejecutar migración de BD (obligatorio, no es automático)

```powershell
docker compose exec backend alembic upgrade head
```

### 2.5 Crear primer super_admin (solo primera vez)

```powershell
@'
import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionFactory
from app.models.enums import UserRole, UserStatus
from app.models.user import User
from app.core.security import hash_password, normalize_email

async def main():
    async with AsyncSessionFactory() as db:
        email = normalize_email("superadmin@local.dev")
        r = await db.execute(select(User).where(User.email == email))
        if r.scalar_one_or_none():
            print("EXISTS:" + email)
            return
        db.add(User(
            email=email,
            first_name="Platform",
            last_name="Admin",
            password_hash=hash_password("ChangeMe123!Strong"),
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
            company_id=None,
            must_change_password=True,
        ))
        await db.commit()
        print("CREATED:" + email)

asyncio.run(main())
'@ | docker compose exec -T backend python -
```

### 2.6 Levantar frontend manual

```powershell
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

### 2.7 (Opcional) Levantar todo con Docker, incluyendo frontend

```powershell
docker compose up --build -d
docker compose exec backend alembic upgrade head
```

### 2.8 (Opcional) Levantar pgAdmin

```powershell
docker run -d --name licitaciones-pgadmin --network hackatoon_default -p 5050:80 -e PGADMIN_DEFAULT_EMAIL=admin@local.dev -e PGADMIN_DEFAULT_PASSWORD=admin dpage/pgadmin4
```

## 3. Comandos cuando ya existen imágenes/contenedores

Todos los comandos se ejecutan desde la raíz del repositorio, salvo que se indique lo contrario.

### 3.1 Iniciar servicios

Iniciar DB + backend + worker (recomendado):

```powershell
docker compose up -d db backend worker
```

Iniciar todos los servicios definidos en compose (incluye frontend si se usa):

```powershell
docker compose up -d
```

Iniciar un servicio específico:

```powershell
docker compose up -d db
docker compose up -d backend
docker compose up -d worker
```

### 3.2 Detener servicios

Detener servicios sin eliminarlos:

```powershell
docker compose stop
```

Detener un servicio específico:

```powershell
docker compose stop backend
docker compose stop worker
docker compose stop db
```

### 3.3 Reiniciar servicios

Reiniciar todos los servicios del compose:

```powershell
docker compose restart
```

Reiniciar un servicio específico:

```powershell
docker compose restart backend
docker compose restart worker
docker compose restart db
```

### 3.4 Ver estado y logs

Estado:

```powershell
docker compose ps -a
```

Logs (últimas líneas):

```powershell
docker compose logs --tail=100
docker compose logs --tail=100 backend
docker compose logs --tail=100 worker
docker compose logs --tail=100 db
```

Logs en vivo:

```powershell
docker compose logs -f backend
```

### 3.5 Apagar y eliminar contenedores

Detener y eliminar contenedores/red del compose (mantiene volúmenes, **no borra la BD**):

```powershell
docker compose down
```

Detener y eliminar contenedores + volúmenes (**borra datos de BD**):

```powershell
docker compose down -v
```

### 3.6 Reconstruir cuando hay cambios

Reconstruir imágenes y levantar:

```powershell
docker compose up --build -d db backend worker
```

Reconstruir solo un servicio:

```powershell
docker compose up --build -d backend
```

### 3.7 Comandos útiles de BD

Aplicar migraciones:

```powershell
docker compose exec backend alembic upgrade head
```

Ver tablas por consola:

```powershell
docker compose exec db psql -U licitaciones -d licitaciones -c "\dt"
```

Abrir psql interactivo:

```powershell
docker compose exec db psql -U licitaciones -d licitaciones
```

### 3.8 Comandos útiles de pgAdmin opcional

Iniciar pgAdmin existente:

```powershell
docker start licitaciones-pgadmin
```

Detener pgAdmin:

```powershell
docker stop licitaciones-pgadmin
```

Eliminar pgAdmin (si se quiere recrear):

```powershell
docker rm -f licitaciones-pgadmin
```

## 4. Notas importantes

- `docker-compose.yml` usa `backend/.env.example` y `frontend/.env.example` como `env_file`. Para desarrollo local rápido funciona así; para personalizar, ajustar el compose o los env files con cuidado.
- La migración **no se ejecuta automáticamente** al hacer `docker compose up`; siempre ejecutar `alembic upgrade head` después de levantar la BD por primera vez (o cuando haya nuevas migraciones).
- El primer `super_admin` no se crea automáticamente.
- El frontend se puede correr manualmente con `npm install` y `npm run dev`; en ese caso no hace falta levantar el servicio `frontend` de Docker Compose.
- No exponer puertos de BD ni usar estas credenciales en producción.
