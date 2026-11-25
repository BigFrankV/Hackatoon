# Guía del proyecto — Licitaciones AI (Módulo Auth/RBAC/Multitenancy)

## 1. Estado actual

El módulo correspondiente al **doc 2** (login, autenticación, RBAC, multitenancy, administración de empresas/usuarios y vistas por rol) está implementado por tramos (1 a 4).

Verificaciones realizadas durante la implementación:
- Backend: `pytest -q` → **48 passed**.
- Backend: `ruff check` en cambios del Tramo 3 → **All checks passed**.
- Frontend: `npm run build` → **OK** (`tsc --noEmit && vite build`).
- Docker: `docker compose config` → **OK**.

> Nota: no se ejecutó una prueba E2E manual nueva en esta guía. Antes de pasar a producción, se recomienda una validación integrada completa.

## 2. Recorrido del backend

Ruta base: `backend/`

### 2.1 Configuración e infraestructura

| Archivo | Propósito | Elementos clave |
|---|---|---|
| `.env.example` | Plantilla de variables de entorno | `APP_NAME`, `ENVIRONMENT`, `API_V1_PREFIX`, `DEBUG`, `LOG_LEVEL`, `SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `REFRESH_COOKIE_*`, `LOGIN_RATE_LIMIT_*`, `LOGIN_LOCKOUT_*`, `DATABASE_URL`, `DATABASE_ECHO`, `CORS_ORIGINS` |
| `Dockerfile` | Imagen backend | Python 3.12-slim, instala dependencias, expone `8000`, ejecuta Uvicorn |
| `requirements.txt` | Dependencias runtime | FastAPI, Uvicorn, Pydantic v2, SQLAlchemy async, asyncpg, Alembic, psycopg, argon2-cffi, PyJWT, etc. |
| `requirements-dev.txt` | Dependencias dev/test | pytest, pytest-asyncio, httpx, aiosqlite, ruff |
| `pytest.ini` | Configuración pytest | `testpaths=app/tests`, `asyncio_mode=auto` |
| `ruff.toml` | Lint | Ignora `B008` para `Depends(...)` |
| `alembic.ini` | Config Alembic | `script_location=alembic`; URL tomada desde settings en `alembic/env.py` |

### 2.2 Entrada y wiring

| Archivo | Propósito | Funciones/endpoints clave |
|---|---|---|
| `app/main.py` | Crea app FastAPI | Configura OpenAPI/docs, CORS, handlers de error (`app_error_handler`, `validation_error_handler`, `http_exception_handler`), incluye router v1 |
| `app/api/v1/router.py` | Agrega routers v1 | Incluye `health`, `auth`, `companies`, `company`, `users`, `audit` |
| `app/api/v1/health.py` | Healthcheck | `GET /api/v1/health` → `{"status":"ok"}` |

### 2.3 Core

| Archivo | Propósito | Elementos clave |
|---|---|---|
| `app/core/config.py` | Configuración central | `Settings(BaseSettings)`, `parse_cors_origins`, `sqlalchemy_database_uri`, `alembic_database_uri`, `get_settings()` |
| `app/core/security.py` | Seguridad/cripto/tokens | `normalize_email`, `hash_password`, `verify_password`, `create_access_token`, `decode_access_token`, `generate_refresh_token`, `hash_refresh_token`, `generate_temporary_password` |
| `app/core/permissions.py` | Matriz de permisos | `PERMISSIONS`, `roles_for_permission`, `permissions_for_role` |
| `app/core/exceptions.py` | Errores de aplicación | `AppError`, `NotFoundError`, `PermissionDeniedError`, `AuthenticationError`, `BadRequestError`, `ConflictError`, `RateLimitError` |
| `app/core/rate_limit.py` | Rate limit en memoria | `InMemoryRateLimiter.hit/reset`, `login_rate_limiter` (limitación: por proceso) |
| `app/core/logging.py` | Logging básico | `configure_logging()` |

### 2.4 Base de datos

| Archivo | Propósito | Elementos clave |
|---|---|---|
| `app/db/base.py` | Base declarativa | `Base(DeclarativeBase)` |
| `app/db/session.py` | Sesión async | engine async, `AsyncSessionFactory`, `get_db()` |
| `app/api/dependencies/database.py` | Dependencia DB | Reexporta `get_db` |

### 2.5 Modelos

| Archivo | Propósito | Elementos clave |
|---|---|---|
| `app/models/enums.py` | Enums de dominio | `CompanyStatus`, `UserRole`, `UserStatus` |
| `app/models/company.py` | Empresa | Tabla `companies`; campos de identidad/contacto/estado; relación `users` |
| `app/models/user.py` | Usuario | Tabla `users`; constraint `ck_users_role_company_id`; email único; password hash; estado; lockout; relaciones |
| `app/models/refresh_token.py` | Refresh tokens | Tabla `refresh_tokens`; guarda solo `token_hash`; family/revocación/reuso/reemplazo |
| `app/models/audit_log.py` | Auditoría | Tabla `audit_logs`; actor/company/entity/action; `event_metadata` mapeado a columna `metadata` |
| `app/models/__init__.py` | Exportación | Exporta modelos y `Base` |

### 2.6 Schemas (Pydantic)

| Archivo | Propósito | Schemas clave |
|---|---|---|
| `app/schemas/common.py` | Base estricta | `StrictSchema` (`extra="forbid"`), `MessageResponse` |
| `app/schemas/auth.py` | Auth/perfil/sesiones | `LoginRequest/Response`, `RefreshResponse`, `ProfileUpdateRequest`, `ChangePasswordRequest`, `SessionResponse`, `UserPublic` |
| `app/schemas/company.py` | Empresas | Create/update/status/profile/response; creación incluye admin inicial y password temporal |
| `app/schemas/user.py` | Usuarios admin | `CompanyUserCreateRequest`, `GlobalUserCreateRequest`, `GlobalUserUpdateRequest`, `UserResetPasswordResponse`, `UserCreatedResponse` |
| `app/schemas/audit.py` | Auditoría | `AuditLogResponse`, `AuditLogListResponse`, `AuditLogFilters` |

### 2.7 Servicios (lógica de negocio)

| Archivo | Propósito | Funciones clave |
|---|---|---|
| `app/services/audit_service.py` | Auditoría | `record_audit_event`, `list_audit_logs`; sanitiza metadata sensible |
| `app/services/auth_service.py` | Auth/sesión | `login`, `refresh_tokens`, `logout`, `update_profile`, `change_password`, `list_sessions`, `revoke_session`, `revoke_user_sessions`, `revoke_company_sessions` |
| `app/services/user_service.py` | Admin usuarios | `list_users_global`, `create_user_global`, `get_user_global`, `update_user_global`, `set_user_status_global`, `reset_user_password_global`, `revoke_user_sessions_global`, y versiones `*_company_*_scoped` |
| `app/services/company_service.py` | Admin empresas | `list_companies`, `create_company`, `get_company`, `update_company`, `suspend_company`, `activate_company`, `get_company_profile`, `update_company_profile`, `list_company_users`, `create_company_user` |

### 2.8 Dependencias API

| Archivo | Propósito | Funciones clave |
|---|---|---|
| `app/api/dependencies/auth.py` | Usuario autenticado | `get_current_user` (JWT, tipo, usuario activo, empresa activa) |
| `app/api/dependencies/permissions.py` | Autorización | `require_permissions`, `require_roles` |
| `app/api/dependencies/database.py` | DB | `get_db` |

### 2.9 Endpoints API v1

Prefijo: `/api/v1`

| Archivo | Alcance | Endpoints principales |
|---|---|---|
| `app/api/v1/health.py` | Público | `GET /health` |
| `app/api/v1/auth.py` | Sesión propia | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`, `PATCH /auth/me`, `POST /auth/change-password`, `GET /auth/sessions`, `DELETE /auth/sessions/{session_id}` |
| `app/api/v1/companies.py` | Super admin | `GET/POST /companies`, `GET/PATCH /companies/{company_id}`, `POST /companies/{company_id}/suspend`, `POST /companies/{company_id}/activate`, `GET/POST /companies/{company_id}/users` |
| `app/api/v1/company.py` | Admin de empresa | `GET/PATCH /company/profile`, `GET/POST /company/users`, `GET/PATCH /company/users/{user_id}`, `activate/deactivate/reset-password/revoke-sessions`, `GET /company/audit-logs` |
| `app/api/v1/users.py` | Super admin | `GET/POST /users`, `GET/PATCH /users/{user_id}`, `activate/deactivate/reset-password/revoke-sessions` |
| `app/api/v1/audit.py` | Super admin | `GET /audit-logs` |

### 2.10 Workers, Alembic y tests

| Ruta | Propósito | Detalle |
|---|---|---|
| `app/workers/main.py` | Worker placeholder | Loop de espera; no procesa jobs reales todavía |
| `alembic/env.py` | Integración Alembic | Usa settings + metadata de modelos |
| `alembic/versions/0001_initial_identity.py` | Migración inicial | Crea `companies`, `users`, `refresh_tokens`, `audit_logs` y constraints |
| `app/tests/conftest.py` | Fixtures de test | SQLite async en memoria, cliente ASGI, reset rate limiter |
| `app/tests/test_identity_models.py` | Tests de modelos | Constraints y defaults |
| `app/tests/test_migrations.py` | Test de migración | `alembic upgrade head` en SQLite |
| `app/tests/test_auth.py` | Tests de auth | Login/refresh/logout/perfil/password/sesiones/casos críticos |
| `app/tests/test_tramo3_rbac.py` | Tests RBAC/multitenancy | Permisos, aislamiento entre empresas, suspensión/desactivación, auditoría |

## 3. Recorrido del frontend

Ruta base: `frontend/`

### 3.1 Configuración

| Archivo | Propósito |
|---|---|
| `package.json` | Scripts: `dev`, `build`, `preview`; dependencias React/Router |
| `vite.config.ts` | Vite + React, alias `@`, puerto 5173 |
| `tailwind.config.js`, `postcss.config.js` | Estilos |
| `tsconfig.json`, `tsconfig.node.json` | TypeScript estricto |
| `.env.example` | `VITE_API_BASE_URL`, `VITE_APP_NAME` |
| `Dockerfile` | Dev server Vite (opcional; se recomienda correr front manual en desarrollo) |
| `index.html` | Punto de montaje SPA |

### 3.2 Entrada y router

| Archivo | Propósito | Elementos clave |
|---|---|---|
| `src/main.tsx` | Bootstrap | `BrowserRouter` + `AuthProvider` |
| `src/App.tsx` | App root | Renderiza `AppRouter` |
| `src/app/router/AppRouter.tsx` | Rutas | Rutas públicas, plataforma, app, admin, placeholders, 403/404 |
| `src/app/router/guards.tsx` | Guards | `RequireAuth`, `RequireRoles`, `RequirePermission`, `PublicOnly` |
| `src/app/providers/AppProviders.tsx` | Provider placeholder | Passthrough |

### 3.3 Librerías cliente

| Archivo | Propósito | Elementos clave |
|---|---|---|
| `src/lib/api/client.ts` | Cliente HTTP | `apiRequest<T>`, Bearer en memoria, `credentials: "include"`, refresh en 401 una vez, `ApiRequestError` |
| `src/lib/auth/authApi.ts` | API auth | `loginRequest`, `refreshRequest`, `logoutRequest`, `meRequest`, `updateProfileRequest`, `changePasswordRequest` |
| `src/lib/auth/AuthProvider.tsx` | Contexto de sesión | Bootstrap, `login`, `logout`, `refreshUser`, `updateProfile`, `changePassword`, `useAuth` |
| `src/lib/permissions/index.ts` | Permisos UX | `hasRole`, `hasPermission`, `canAccessPlatform`, `canAccessApp` (backend sigue siendo autoridad) |
| `src/lib/format.ts` | Formato UI | `formatDateTime`, `formatDate`, `formatStatus`, `statusTone` |
| `src/lib/api/companies.ts` | API empresas plataforma | Wrappers `/companies...` |
| `src/lib/api/company.ts` | API empresa/admin | Wrappers `/company...` |
| `src/lib/api/users.ts` | API usuarios globales | Wrappers `/users...` |
| `src/lib/api/audit.ts` | API auditoría | Wrappers `/audit-logs`, `/company/audit-logs` |

### 3.4 Tipos, layout y UI

| Ruta | Propósito |
|---|---|
| `src/types/index.ts` | Tipos TS para auth, users, companies, audit, errores, paginación |
| `src/components/layout/nav.ts` | Navegación por rol |
| `src/components/layout/ShellLayout.tsx` | Layout base responsive con sidebar |
| `src/components/layout/AppLayout.tsx` | Layout de `/app` según rol |
| `src/components/layout/PlatformLayout.tsx` | Layout de `/platform` para super_admin |
| `src/components/ui/*.tsx` | `Alert`, `Badge`, `Button`, `ConfirmDialog`, `EmptyState`, `Input`, `PageLoader`, `Pagination`, `Select` |

### 3.5 Features / páginas

| Ruta | Propósito |
|---|---|
| `src/features/auth/LoginPage.tsx` | Login real |
| `src/features/auth/ForbiddenPage.tsx` | 403 |
| `src/features/auth/NotFoundPage.tsx` | 404 |
| `src/features/dashboard/DashboardPage.tsx` | Dashboard por rol |
| `src/features/profile/ProfilePage.tsx` | Perfil y cambio de contraseña |
| `src/features/platform/*` | Dashboard plataforma, empresas, usuarios globales, auditoría global |
| `src/features/company/*` | Config empresa, usuarios empresa, auditoría empresa |
| `src/features/placeholders/ModulePlaceholderPage.tsx` | Placeholders para módulos futuros |

### 3.6 Rutas actuales

- **Públicas**: `/login`, `/forbidden`, `*`
- **Super admin**: `/platform`, `/platform/companies`, `/platform/companies/new`, `/platform/companies/:companyId`, `/platform/users`, `/platform/users/new`, `/platform/users/:userId`, `/platform/audit`, `/app/profile`
- **Admin**: `/app`, `/app/profile`, `/app/settings/company`, `/app/settings/users`, `/app/settings/users/new`, `/app/settings/users/:userId`, `/app/settings/audit`, placeholders operativos
- **User**: `/app`, `/app/profile`, placeholders operativos (`/app/vault`, `/app/tenders`, `/app/analysis`, `/app/chat`, `/app/offers`)

## 4. Base de datos y migraciones

### ¿La migración está lista?

Sí. La migración inicial está lista en:
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/versions/0001_initial_identity.py`

Crea las tablas: `companies`, `users`, `refresh_tokens`, `audit_logs`.

### Punto importante

`docker-compose.yml` **no ejecuta migraciones automáticamente**. Después de levantar la base de datos, se debe ejecutar:

```bash
alembic upgrade head
```

## 5. Ejecución local recomendada (DB + backend en Docker, frontend manual)

Esta opción evita cargar el frontend dentro de Docker durante desarrollo.

### 5.1 Prerrequisitos

- Docker Desktop / Docker Compose
- Python 3.12+ (recomendado para scripts/herramientas locales backend)
- Node.js 22+ (frontend manual)

### 5.2 Preparar variables de entorno

Desde la raíz del proyecto:

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env
```

Revisar valores mínimos:

- `backend/.env`
  - `SECRET_KEY`: cambiar el valor de desarrollo.
  - `DATABASE_URL`: para backend en Docker Compose se sobreescribe a `db`; para backend manual local usar `localhost:5432`.
  - `CORS_ORIGINS`: incluir `http://localhost:5173`.
- `frontend/.env`
  - `VITE_API_BASE_URL=http://localhost:8000/api/v1`

> Observación: el `docker-compose.yml` actual referencia `env_file: ./backend/.env.example` y `./frontend/.env.example`. Si se desea usar `.env`, ajustar `docker-compose.yml` en consecuencia.

### 5.3 Levantar DB, backend y worker (sin frontend)

Desde la raíz:

```powershell
docker compose up --build db backend worker
```

Servicios:
- PostgreSQL: `localhost:5432`
- Backend: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/health`

### 5.4 Ejecutar migraciones

Con contenedores activos:

```powershell
docker compose exec backend alembic upgrade head
```

Alternativa local (backend manual, venv activo, DB accesible):

```powershell
cd backend
.\.venv\Scripts\activate
alembic upgrade head
```

### 5.5 Levantar frontend manual

En otra terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

### 5.6 Crear primer super_admin (bootstrap inicial)

Actualmente no existe seed automático para el primer `super_admin`. Se puede crear una vez con un script temporal.

Crear `backend/bootstrap_superadmin.py`:

```python
import asyncio

from sqlalchemy import select

from app.core.security import hash_password, normalize_email
from app.db.session import AsyncSessionFactory
from app.models.enums import UserRole, UserStatus
from app.models.user import User


async def main() -> None:
    email = normalize_email("superadmin@local.dev")
    password = "ChangeMe123!Strong"

    async with AsyncSessionFactory() as db:
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            print("super_admin already exists:", email)
            return

        user = User(
            email=email,
            first_name="Platform",
            last_name="Admin",
            password_hash=hash_password(password),
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
            company_id=None,
            must_change_password=True,
        )
        db.add(user)
        await db.commit()
        print("super_admin created:", email)


if __name__ == "__main__":
    asyncio.run(main())
```

Ejecutar desde `backend` con el entorno activo y DB accesible:

```powershell
cd backend
.\.venv\Scripts\activate
python bootstrap_superadmin.py
```

Después de crear el usuario, eliminar el archivo temporal. Iniciar sesión en `http://localhost:5173/login` y cambiar la contraseña.

## 6. Ejecución alternativa con Docker Compose completo

Si se desea levantar también el frontend en Docker:

```powershell
docker compose up --build
```

Luego ejecutar migraciones:

```powershell
docker compose exec backend alembic upgrade head
```

## 7. Despliegue base (guía)

### 7.1 Base de datos

- PostgreSQL 16 gestionado o contenedor con persistencia.
- Habilitar `pgvector`.
- Backups automáticos y pruebas de restauración.
- No exponer el puerto de BD públicamente.

### 7.2 Backend

- Ejecutar detrás de reverse proxy (Nginx/Caddy/Traefik) con HTTPS.
- Configurar secrets/env reales: `SECRET_KEY`, `ENVIRONMENT=production`, `REFRESH_COOKIE_SECURE=true`, `CORS_ORIGINS` del dominio frontend.
- Ejecutar `alembic upgrade head` en cada release.
- Considerar rate limiting compartido (Redis) para despliegues multi-worker; la implementación actual es en memoria.

### 7.3 Frontend

- Para producción, preferir build estático:

```powershell
cd frontend
npm install
npm run build
```

- Servir `frontend/dist/` con Nginx/CDN/hosting estático.
- Configurar `VITE_API_BASE_URL` apuntando al backend público `/api/v1`.

### 7.4 Orden sugerido de despliegue

1. Provisionar BD.
2. Configurar variables/secrets.
3. Desplegar backend.
4. Ejecutar `alembic upgrade head`.
5. Crear primer `super_admin` (solo primera vez).
6. Desplegar frontend estático.
7. Validar login, refresh, RBAC, suspensión de empresa y aislamiento multitenant.

## 8. Observaciones y pendientes

- `README.md` está desactualizado (describe Tramo 1); esta guía refleja el estado actual del módulo auth/RBAC.
- No existe bootstrap automático de `super_admin`; se documenta un procedimiento manual inicial.
- El worker es placeholder; no hay procesamiento asíncrono real todavía.
- Los módulos de bóveda, licitaciones, análisis, chat y ofertas están como placeholders en frontend.
- El rate limit de login es en memoria (no distribuido).
- `docker-compose.yml` no ejecuta migraciones automáticamente.
