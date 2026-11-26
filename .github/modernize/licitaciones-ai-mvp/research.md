# Planning Research and Decisions

**Checked**: 2026-11-26

## Mercado Público Integration

- **Decision**: Use the official Mercado Público API as the public opportunity
  source, behind a backend adapter. Keep manual document upload as an independent
  fallback.
- **Evidence**: The [official ChileCompra API page](https://www.chilecompra.cl/api/)
  documents the public `licitaciones.json` service and queries by tender code,
  date, state, supplier code, and public-organization code. It states date/state
  listings return basic information and lookup by code returns detailed
  information. Access requires a ticket requested through Clave Única.
- **Security constraint**: The published API examples put the ticket in the
  query string. Keep it server-side and redact upstream URLs from application,
  proxy, and error logs.
- **Unresolved validation gate**: The page displayed an API unavailability
  banner image when checked; the message was not available as text. No valid
  project ticket was provided, and the guide PDF's response schema and document
  download behavior could not be verified. Before implementing automatic
  retrieval, obtain a valid ticket and test availability, sample responses,
  ticket behavior, rate limits, and attachment links. Do not assume attachments
  are downloadable from the API.

## AI Provider Strategy

- **Decision**: Start with local Ollama. The user selected the downloaded
  `qwen3:1.7b` model for chat and `bge-m3` at 1024 dimensions for embeddings.
  The backend connects to the local Ollama service; hosted API integrations are
  deferred to a later phase. Keep server-side provider interfaces so they can
  be added without changing business rules.
- **Runtime boundary**: A browser on the user's PC must not call Ollama
  directly. The backend and worker use the configured local Ollama endpoint.
- **Embedding invariant**: Changing a chat model must not change stored vectors.
  Changing the embedding model requires an explicit migration/re-index plan;
  incompatible vector dimensions must not be mixed.

## Processing and Storage

- **Planning default**: Use the proposed durable processing-job records and the
  existing worker container as the first execution boundary. Do not add a queue
  broker unless a measured reliability or scale requirement justifies it.
- **Storage decision**: Use private local storage for development. Defer the
  production object-storage provider until the cloud target is selected. Keep
  the application behind a private storage interface; do not expose storage
  credentials to the frontend.
- **Deletion decision**: Use reversible archival for tracked tenders and
  logical deletion for documents, conversations, and offers; preserve
  audit/history and do not automatically purge files or records in the MVP.
  Define hard-purge retention before production.
- **Database**: The user selected relational role/permission tables and
  approved the physical-schema defaults: tenant consistency constraints,
  explicit state/range checks, restrictive provenance-preserving deletes, and
  domain-sliced additive migrations. Revision `0002_relational_rbac` backfills
  current role values while preserving authorization behavior.

## Validation Baseline

- Backend canonical local test command: `python -m pytest` from `backend/`;
  baseline: 53 passed, 0 failed on 2026-11-26. The current fixture uses
  in-memory SQLite, not PostgreSQL.
- Frontend build command: `npm run build` from `frontend/`; baseline passed.
- Docker daemon check (`docker info`): unavailable in this planning environment.
- Node.js: available, version `v22.13.1`.
- Frontend has no existing browser-test suite or Playwright dependency.
  `npx --no-install playwright --version` failed because Playwright is not
  installed; the implementation setup must add the dependency and attempt a
  Chromium install.
- The backend test run emitted 48 PyJWT HMAC key-length warnings. This is
  recorded as baseline evidence, not expanded into an unrelated task.

## Plan Boundaries

- Preserve the existing authentication/session behavior and company identity.
- Add feature modules within the current backend/frontend repository; do not
  split to microservices.
- Add a CI workflow for build, tests, and migration checks. Production CD is
  not specified because no target cloud, environment, or deployment approvals
  have been chosen.
