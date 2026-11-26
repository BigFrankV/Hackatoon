# Existing Technology Stack

This document records the stack currently declared in repository manifests and
container files. It does not select a target stack for planned features.

## Runtime and Frameworks

| Area | Current technology | Evidence |
|---|---|---|
| Backend language/runtime | Python 3.12 (`python:3.12-slim`) | `backend/Dockerfile` |
| HTTP API | FastAPI `>=0.115.0,<1.0.0`; Uvicorn `>=0.30.0,<1.0.0` | `backend/requirements.txt` |
| Validation/configuration | Pydantic `>=2.7.0,<3.0.0`; pydantic-settings `>=2.3.0,<3.0.0` | `backend/requirements.txt` |
| ORM/database | SQLAlchemy async `>=2.0.30,<3.0.0`; asyncpg `>=0.29.0,<1.0.0`; psycopg `>=3.2.0,<4.0.0` | `backend/requirements.txt` |
| Migrations | Alembic `>=1.13.2,<2.0.0` | `backend/requirements.txt`, `backend/alembic/` |
| Relational database | PostgreSQL 16 image (`pgvector/pgvector:pg16`) in local Compose | `docker-compose.yml` |
| Frontend runtime | Node 22 Alpine container | `frontend/Dockerfile` |
| Frontend framework | React and React DOM `^18.3.1` | `frontend/package.json` |
| Frontend routing/build | React Router DOM `^6.26.2`; Vite `^5.4.8`; TypeScript `^5.6.2` | `frontend/package.json` |
| Frontend styling | Tailwind CSS `^3.4.13`, PostCSS, Autoprefixer | `frontend/package.json` |

## Other Declared Backend Dependencies

`argon2-cffi` for password hashing, `PyJWT` for JWT handling,
`python-multipart` for multipart requests, and `email-validator` for email
validation. Development/test dependencies include pytest, pytest-asyncio,
httpx, aiosqlite, and Ruff.

## Existing Integration State

- The PostgreSQL image includes pgvector, but the current Alembic migration
  does not enable the extension or create vector tables.
- `backend/app/integrations/ai/`, `extraction/`, and `storage/` currently contain
  no implemented provider clients.
- The worker is an idle placeholder and there is no declared queue/broker
  dependency.
- The frontend API base URL is configured with `VITE_API_BASE_URL`, falling
  back to `http://localhost:8000/api/v1`.

## Versioning Notes

Most Python packages use compatible lower/upper bounds rather than pinned
versions. Frontend versions use npm semver ranges and a lockfile. Runtime
behavior should therefore be validated against the lockfiles and resolved
container dependencies at implementation time.
