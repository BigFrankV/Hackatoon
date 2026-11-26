# Project Structure

## Scope

This is a focused architecture view of the existing components that the
Licitaciones AI MVP must integrate with. It is not a complete per-endpoint or
per-page behavior inventory. Authentication and company administration are
existing foundations; tender, document, analysis, chat, and offer workflows are
not implemented yet.

## Project Type

Full-stack web application organized as a backend application and a frontend
application in one repository. The backend is a FastAPI modular monolith; the
frontend is a React SPA. Local development uses Docker Compose with PostgreSQL
and optional pgAdmin, worker, and frontend services.

## Runtime Entry Points

| Entry point | Location | Role |
|---|---|---|
| FastAPI application | `backend/app/main.py` | Creates the application, installs CORS and exception handlers, mounts the versioned API router. |
| API router | `backend/app/api/v1/router.py` | Registers health, authentication, company, platform-company, user, and audit route modules. |
| Async database session | `backend/app/db/session.py` | Creates the async SQLAlchemy engine/session factory and yields request sessions. |
| Background worker | `backend/app/workers/main.py` | Current placeholder process; loops without processing jobs. |
| Frontend bootstrap | `frontend/src/main.tsx` | Mounts the React application. |
| Frontend route tree | `frontend/src/app/router/AppRouter.tsx` | Defines login, platform administration, company workspace, settings, and placeholder product pages. |

## Existing Layers

- **API and authorization**: `backend/app/api/v1/` and
  `backend/app/api/dependencies/` define HTTP routes and enforce authenticated
  user, role, permission, and company context.
- **Application services**: `backend/app/services/` contains auth, company,
  user, and audit operations. Route handlers call these functions.
- **Persistence**: `backend/app/models/`, `backend/app/db/`, and
  `backend/alembic/` contain SQLAlchemy models, async database setup, and
  versioned migrations.
- **Shared backend concerns**: `backend/app/core/` contains configuration,
  security, permissions, errors, logging, and rate limiting.
- **Frontend features**: `frontend/src/features/` contains auth, platform,
  company, dashboard, profile, and placeholder pages. Shared layout and UI
  components live under `frontend/src/components/`.
- **Frontend API/auth state**: `frontend/src/lib/api/` and
  `frontend/src/lib/auth/` provide API requests and authentication state.

## Product Domains: Current State

| Domain | Current state |
|---|---|
| Authentication and sessions | Implemented; access tokens are held in memory and refresh tokens use an HTTP-only cookie. |
| Company identity and user administration | Implemented with server-side role/permission checks and company-scoped services. |
| Audit | Implemented for identity/company administration. |
| Procurement opportunities and tracking | Frontend placeholder; no Mercado Público client or persistence entities. |
| Document storage and processing | Integration package placeholders; no implemented ingestion pipeline. |
| RAG and AI chat | No implemented provider, embeddings, retrieval, or chat persistence. |
| Analysis and offer preparation | Frontend placeholders; no implemented domain services. |
| Background jobs | Worker is a placeholder; no queue or durable job processing is configured. |

## Configuration and Build Files

- `docker-compose.yml`: local services, PostgreSQL, migrations, bootstrap, demo
  seeding, backend, and optional worker/frontend/pgAdmin profiles.
- `backend/requirements.txt`, `backend/requirements-dev.txt`: backend runtime
  and development dependencies.
- `backend/Dockerfile`: Python API/worker image.
- `frontend/package.json`, `frontend/package-lock.json`: frontend dependencies
  and scripts.
- `frontend/vite.config.ts`: Vite React plugin, alias, and dev server settings.
- `frontend/Dockerfile`: Node frontend image.
- `backend/alembic/`: migration environment and current initial schema.

## Planning Boundary

The new product domains should integrate through the existing authenticated API
and company context. The precise module/unit boundaries for those new domains
remain planning decisions; this document does not prescribe a rewrite, service
split, or final module count.
