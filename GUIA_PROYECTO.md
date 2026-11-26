# Guía del proyecto — Licitaciones AI (Módulo Auth/RBAC/Multitenancy)

## 1. Estado actual

Implementado: autenticación, sesiones, perfil, RBAC, administración de empresas y usuarios, aislamiento multiempresa y auditoría. También hay carga privada PDF/DOCX, extracción por página, chunking, embeddings BGE-M3 en pgvector y chat local con Ollama y citas filtradas por empresa. La pantalla Licitaciones consulta fichas públicas por código a Mercado Público; el ticket queda en el backend.

Pendiente: seguimiento persistente de licitaciones, descarga de sus bases, selección/políticas de modelos por empresa, análisis Go/No-Go y preparación de ofertas. No existe despliegue CI/CD a producción.

Usa los comandos de pruebas de este documento para validar el estado actual. No se fija aquí un conteo de pruebas, porque cambia a medida que se añaden casos.

## 2. Recorrido del backend

Ruta base: `backend/`

### 2.1 Configuración e infraestructura

| Archivo | Propósito | Elementos clave |
|---|---|---|
| `.env.example` | Plantilla de variables de entorno | `APP_NAME`, `ENVIRONMENT`, `API_V1_PREFIX`, `DEBUG`, `LOG_LEVEL`, `SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `REFRESH_COOKIE_*`, `LOGIN_RATE_LIMIT_*`, `LOGIN_LOCKOUT_*`, `DATABASE_URL`, `DATABASE_ECHO`, `CORS_ORIGINS` |
| `Dockerfile` | Imagen backend | Python 3.12-slim, instala dependencias, expone `8000`, ejecuta Uvicorn |
| `requirements.txt` | Dependencias runtime | FastAPI, Uvicorn, SQLAlchemy async, Alembic, Ollama HTTP client, PyMuPDF, python-docx, pgvector, etc. |
| `requirements-dev.txt` | Dependencias dev/test | pytest, pytest-asyncio, httpx, aiosqlite, ruff |
| `pytest.ini` | Configuración pytest | `testpaths=app/tests`, `asyncio_mode=auto` y marca `integration` |
| `ruff.toml` | Lint | Ignora `B008` para `Depends(...)` |
| `alembic.ini` | Config Alembic | `script_location=alembic`; URL tomada desde settings en `alembic/env.py` |

### 2.2 Entrada y wiring

| Archivo | Propósito | Funciones/endpoints clave |
|---|---|---|
| `app/main.py` | Crea app FastAPI | Configura OpenAPI/docs, CORS, handlers de error (`app_error_handler`, `validation_error_handler`, `http_exception_handler`), incluye router v1 |
| `app/api/v1/router.py` | Agrega routers v1 | Incluye `health`, `auth`, `companies`, `company`, `users`, `audit`, `documents`, `chat` |
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
| `app/models/knowledge.py` | Documentos y chat | Catálogo Ollama, documentos/versiones, extracciones/chunks/embeddings, conversaciones/mensajes/citas |
| `app/models/__init__.py` | Exportación | Exporta modelos y `Base` |

### 2.6 Schemas (Pydantic)

| Archivo | Propósito | Schemas clave |
|---|---|---|
| `app/schemas/common.py` | Base estricta | `StrictSchema` (`extra="forbid"`), `MessageResponse` |
| `app/schemas/auth.py` | Auth/perfil/sesiones | `LoginRequest/Response`, `RefreshResponse`, `ProfileUpdateRequest`, `ChangePasswordRequest`, `SessionResponse`, `UserPublic` |
| `app/schemas/company.py` | Empresas | Create/update/status/profile/response; creación incluye admin inicial y password temporal |
| `app/schemas/user.py` | Usuarios admin | `CompanyUserCreateRequest`, `GlobalUserCreateRequest`, `GlobalUserUpdateRequest`, `UserResetPasswordResponse`, `UserCreatedResponse` |
| `app/schemas/audit.py` | Auditoría | `AuditLogResponse`, `AuditLogListResponse`, `AuditLogFilters` |
| `app/schemas/documents.py`, `app/schemas/chat.py` | Repositorio y chat | Contratos de carga/listado/reintento y de mensajes/citas |

### 2.7 Servicios (lógica de negocio)

| Archivo | Propósito | Funciones clave |
|---|---|---|
| `app/services/audit_service.py` | Auditoría | `record_audit_event`, `list_audit_logs`; sanitiza metadata sensible |
| `app/services/auth_service.py` | Auth/sesión | `login`, `refresh_tokens`, `logout`, `update_profile`, `change_password`, `list_sessions`, `revoke_session`, `revoke_user_sessions`, `revoke_company_sessions` |
| `app/services/user_service.py` | Admin usuarios | `list_users_global`, `create_user_global`, `get_user_global`, `update_user_global`, `set_user_status_global`, `reset_user_password_global`, `revoke_user_sessions_global`, y versiones `*_company_*_scoped` |
| `app/services/company_service.py` | Admin empresas | `list_companies`, `create_company`, `get_company`, `update_company`, `suspend_company`, `activate_company`, `get_company_profile`, `update_company_profile`, `list_company_users`, `create_company_user` |
| `app/services/document_service.py` | Documentos | Carga privada, versiones, estado, descarga autenticada, reintentos y pipeline de extracción/embeddings |
| `app/services/chat_service.py` | Chat/RAG | Contexto de empresa, búsqueda pgvector, persistencia de mensajes y citas |

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
| `app/api/v1/documents.py` | Empresa autenticada | `GET/POST /documents`, `GET /documents/{id}/download`, `POST /documents/{id}/retry` |
| `app/api/v1/chat.py` | Empresa autenticada | `POST /chat/messages` |

### 2.10 Workers, Alembic y tests

| Ruta | Propósito | Detalle |
|---|---|---|
| `app/workers/main.py` | Worker durable | Reclama jobs con leases; procesa extracción, chunking y embeddings de documentos |
| `alembic/env.py` | Integración Alembic | Usa settings + metadata de modelos |
| `alembic/versions/0001_initial_identity.py` | Migración inicial | Crea `companies`, `users`, `refresh_tokens`, `audit_logs` y constraints |
| `app/tests/conftest.py` | Fixtures de test | SQLite async en memoria, cliente ASGI, reset rate limiter |
| `app/tests/test_identity_models.py` | Tests de modelos | Constraints y defaults |
| `app/tests/test_migrations.py` | Test de migración | `alembic upgrade head` en SQLite |
| `app/tests/test_auth.py` | Tests de auth | Login/refresh/logout/perfil/password/sesiones/casos críticos |
| `app/tests/test_tramo3_rbac.py` | Tests RBAC/multitenancy | Permisos, aislamiento entre empresas, suspensión/desactivación, auditoría |
| `app/tests/test_bootstrap.py` | Tests de bootstrap | Creación idempotente del superadmin y validación de contraseña |
| `app/tests/test_demo_seed.py` | Tests del seed local | Empresas, usuarios demo e idempotencia |
| `app/tests/test_rate_limit.py` | Tests de rate limit | Expiración y límite del estado en memoria |
| `app/tests/test_user_invariants.py` | Tests de invariantes | Protección del último admin por empresa |

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
| `Dockerfile` | Dev server Vite opcional; el script pregunta si iniciarlo en Docker (por defecto, manual) |
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
| `src/lib/api/documents.ts`, `src/lib/api/chat.ts` | API de producto | Wrappers de carga/listado/reintento y envío de mensajes con citas |

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
| `src/features/documents/VaultPage.tsx` | Bóveda | Carga PDF/DOCX, estado del worker y reintentos |
| `src/features/chat/ChatPage.tsx` | Chat local | Conversación con aviso sin fuentes y citas documentales |
| `src/features/placeholders/ModulePlaceholderPage.tsx` | Placeholders para módulos futuros |

### 3.6 Rutas actuales

- **Públicas**: `/login`, `/forbidden`, `*`
- **Super admin**: `/platform`, `/platform/companies`, `/platform/companies/new`, `/platform/companies/:companyId`, `/platform/users`, `/platform/users/new`, `/platform/users/:userId`, `/platform/audit`, `/app/profile`
- **Admin**: `/app`, `/app/profile`, `/app/settings/company`, `/app/settings/users`, `/app/settings/users/new`, `/app/settings/users/:userId`, `/app/settings/audit`, `/app/vault`, `/app/chat`
- **User**: `/app`, `/app/profile`, `/app/vault`, `/app/chat`; licitaciones, análisis y ofertas aún son placeholders

## 4. Base de datos y migraciones

### ¿La migración está lista?

Sí. Las migraciones Alembic `0001` a `0007` se ejecutan mediante `alembic upgrade head`. Incluyen identidad/RBAC, dominios de producto, jobs y `document_embeddings` con pgvector de 1024 dimensiones, índice HNSW y modelos locales Qwen3/BGE-M3. No insertan empresas demo.

### Punto importante

El servicio `migrate` ejecuta `alembic upgrade head` después de que PostgreSQL esté saludable. Luego, `bootstrap` crea el primer `super_admin` si todavía no existe y `seed-demo` añade dos empresas con un admin y un usuario normal cada una. La API inicia después de que estas tareas de una sola ejecución terminan correctamente. El seeder solo se activa en el perfil local `dev` y no forma parte de las migraciones.

## 5. Desarrollo local con Docker Compose

El flujo local está automatizado con un script de PowerShell. Requiere Docker Desktop con Docker Compose.

### 5.1 Primer inicio

Desde la raíz del repositorio:

```powershell
.\scripts\dev-up.ps1
```

En la primera ejecución se crean `.env`, `backend/.env` y `frontend/.env` desde los ejemplos, sin sobrescribir archivos existentes. Completar en el `.env` raíz:

- `BOOTSTRAP_SUPERADMIN_EMAIL`
- `BOOTSTRAP_SUPERADMIN_PASSWORD` (mínimo 12 caracteres)
- Reemplazar los valores de ejemplo de `POSTGRES_PASSWORD` y `PGADMIN_DEFAULT_PASSWORD` por contraseñas propias.

Volver a ejecutar el script. Si las cuatro variables `DEV_SEED_*_PASSWORD` están vacías, el script genera contraseñas locales y las guarda en el `.env`. Se levantan PostgreSQL, migraciones, bootstrap, datos demo, backend y pgAdmin; pgAdmin registra la conexión local y el script espera que backend y pgAdmin estén saludables. También pregunta si debe iniciar el frontend en Docker. Enter lo deja manual para ejecutarlo desde `frontend/` con `npm run dev`. El bootstrap y el seeder son idempotentes: no reemplazan contraseñas de cuentas existentes.

Los `.env` locales están ignorados por Git. Esta configuración es solo para desarrollo local; no reutilizar las credenciales de ejemplo en despliegues.
Los accesos y la ubicación local de cada contraseña están descritos en [CREDENCIALES_DESARROLLO.md](./CREDENCIALES_DESARROLLO.md); las contraseñas reales no se guardan en la documentación.

### 5.2 Servicios

- Frontend: `http://localhost:5173` (solo si se elige iniciarlo en Docker; si no, iniciar Vite manualmente)
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/health`
- pgAdmin: `http://localhost:5050`
- PostgreSQL desde el host: `localhost:5432`

pgAdmin inicia con el servidor `Licitaciones local` preconfigurado por el script (host `db`, puerto `5432`), sincronizado con `POSTGRES_DB` y `POSTGRES_USER`. Si solicita la contraseña de PostgreSQL, usa `POSTGRES_PASSWORD` del `.env` raíz. El script activa el perfil `jobs`; configura `OLLAMA_BASE_URL` para que backend y worker puedan alcanzar Ollama.

Detener los servicios sin borrar los datos:

```powershell
docker compose --profile dev --profile jobs --profile frontend down
```

PostgreSQL y pgAdmin conservan sus datos en volúmenes separados. No ejecutar `docker compose down --volumes` si se desea preservar la base de datos.

### 5.3 Variables locales

Compose carga la configuración de base de datos y pgAdmin desde el `.env` raíz. La API y Vite usan `backend/.env` y `frontend/.env`, respectivamente. Cambiar los archivos `.env.example` solo modifica los valores iniciales para clones nuevos; no reemplaza los `.env` locales existentes.

## 6. Alcance de CI/CD

La automatización actual prepara y valida el entorno de desarrollo local; no despliega a una nube. El despliegue CI/CD se definirá cuando se seleccione el destino y la estrategia de publicación.

## 7. Despliegue futuro (no configurado)

El Compose actual es de desarrollo: publica PostgreSQL y pgAdmin al host, usa recarga automática y ejecuta el bootstrap local. No usarlo como configuración de producción.

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
npm ci
npm test
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

- El bootstrap de `super_admin` se ejecuta en desarrollo desde las variables del `.env` raíz y no reemplaza cuentas existentes.
- `README.md` y esta guía describen el arranque Docker local; todavía no hay un despliegue CI/CD a nube.
- El worker de documentos usa extracción PDF/DOCX y embeddings; los handlers de análisis aún no existen.
- Los módulos de licitaciones, análisis y ofertas siguen como placeholders; el chat ya cita documentos de la empresa cuando encuentra evidencia.
- El rate limit de login elimina claves inactivas y tiene un límite de estado, pero sigue siendo local al proceso y no distribuido.
