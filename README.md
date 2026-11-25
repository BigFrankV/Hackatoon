# Licitaciones AI
opencode -s ses_dfae867b8ffetwZCgCYivpxQXu
Baseline implementation for the Licitaciones AI platform.

## Tramo 1 scope

This repository currently implements **Tramo 1 (Etapa 0 + Sprint A)**:

- Monorepo structure (`backend/`, `frontend/`)
- Docker Compose for development (`db`, `backend`, `worker`, `frontend`)
- Backend FastAPI skeleton with health endpoint and API docs
- SQLAlchemy 2 async setup
- Alembic configuration and initial migration
- Core identity models: `Company`, `User`, `RefreshToken`, `AuditLog`
- Basic backend tests for schema constraints and model rules
- Frontend scaffold (React + Vite + TypeScript + Tailwind CSS)

Authentication endpoints, full RBAC flows, and auth UI are planned for later tranches.

## Quick start (Docker)

1. Copy environment files:

   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```

2. Start services:

   ```bash
   docker compose up --build
   ```

3. Services:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API docs: http://localhost:8000/docs
   - Health: http://localhost:8000/api/v1/health

## Backend local development

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload
```

## Tests

```bash
cd backend
pytest
```

## Notes

- PostgreSQL uses the `pgvector/pgvector:pg16` image for future vector features.
- Secrets must be provided through environment variables; `.env.example` files contain placeholders only.
- Refresh tokens are modeled as hashes only; plaintext tokens must never be persisted.
