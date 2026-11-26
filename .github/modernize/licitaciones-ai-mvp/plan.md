# Implementation Plan: Licitaciones AI MVP

**Date**: 2026-11-26 | **Spec**: [spec.md](./spec.md)
**Status**: Phase 2 foundations are implemented; the local Ollama document/chat slice is underway. Live Mercado Público integration remains gated on its official API contract and ticket.

## Summary

Complete the multi-company procurement workflow in the existing FastAPI and
React modular monolith. Preserve login and company identity, review the proposed
normalized schema, then add the shared Mercado Público catalogue and tenant-owned
tracking, provider policy, private document processing and retrieval,
evidence-grounded analysis, contextual chat, and versioned offers.

Start with Ollama (`qwen3:1.7b` for chat and `bge-m3` at 1024 dimensions for
embeddings); defer hosted API integrations. Use private local storage during
development. A valid Mercado Público ticket is
required only for live API integration and source retrieval; it does not block
independent work such as RBAC, manual uploads, or local AI capabilities. The
official integration is not assumed to provide tender-document downloads;
manual upload remains an independent path.

## Technical Context

**Language/Version**: Python 3.12 backend; TypeScript 5.6 / React 18 frontend
**Primary Dependencies**: FastAPI, SQLAlchemy async, Alembic, PostgreSQL 16,
React Router, Vite; Ollama is the initial AI provider
**Storage**: PostgreSQL for relational data and approved vector data; private
local storage for development; production object-storage provider deferred
**Testing**: pytest/httpx, PostgreSQL through Docker Compose, Playwright for
browser flows; deterministic HTTP fakes for external APIs/providers
**Target Platform**: Existing local Docker Compose first; cloud deployment
platform not selected
**Performance Goals**: Meet the user-facing outcomes in `spec.md`; no upstream
rate limit or response-time values are assumed until official API validation
**Constraints**: preserve existing auth/session behavior; enforce server-side
tenant isolation; all AI conclusions remain advisory and evidence-linked;
document/analysis jobs need durable state; no microservices or broker without an
evidenced need.

## Constitution Check

| Principle | Plan alignment | Gate |
|---|---|---|
| I. Tenant Isolation and Server-Side Authorization | All new reads/writes, retrieval, files, analyses, chat, and offers use authenticated company context; cross-tenant tests are required. | Aligned |
| II. Evidence-Grounded, Human-Controlled Decisions | Deterministic rules handle hard constraints; findings cite evidence; human decisions are stored separately. | Aligned |
| III. Data Integrity, Provenance, and Auditability | Proposed data model is reviewed before additive migrations; source/document/model versions and audit events are retained. | Aligned |
| IV. Provider-Neutral Integration and Secret Safety | Provider boundaries keep credentials server-side; chat and embedding choices remain separate. | Aligned |
| V. Incremental, Tested, Observable Delivery | Work is divided into independently testable slices with explicit failure/job states. | Aligned |

**Approval gate**: the user approved the specification, proposed data model,
and physical-schema defaults, and ratified constitution v1.0.0. The relational
role backfill is implemented; product migrations must follow the approved
tenant, constraint, and deletion rules. BGE-M3 at 1024 dimensions is selected
and represented by the vector migration. Verify Ollama reachability before its
runtime integration. A valid Mercado Público ticket and live contract checks block only
the live source integration/retrieval work.

## Applied Guidelines

No matching source-to-target migration guideline applies: this is additive
feature work in the existing Python/React stack, not a framework migration.
Keep the current modular-monolith boundary and follow the existing FastAPI
dependency, SQLAlchemy service, Alembic, and React feature-route patterns.

## Implementation Steps

### Phase 1: Setup and Approval Gates

#### Step 1: [Cross-cutting] Approve the product and data baseline

- **Requirements**: REQ-001, REQ-002, REQ-010, REQ-016, REQ-024
- **Design inputs**: `spec.md`, `constitution.md`,
  `../assessment/engines/facts/data-architecture.md`
- **Description**: Treat the product requirements and proposed schema at
  `../assessment/engines/facts/data-architecture.md` as the approved planning
  baseline. Finalize field constraints, tenant ownership, file retention,
  embedding dimensions, and migration boundaries. Use relational role/permission
  tables and define a backfill from the current role enum that preserves existing
  authorization behavior.

#### Step 2: [Cross-cutting] Validate external and model prerequisites

- **Requirements**: REQ-003 through REQ-009, REQ-012, REQ-025
- **Design inputs**: `research.md`, `research/mercado-publico-api.md`,
  `artifacts/tech-stack.md`
- **Description**: Obtain a valid Mercado Público ticket through the user's
  official account and verify service availability, list/detail responses,
  terms, limits, and source document behavior when the ticket is available. If
  not, record that blocker; it gates only live Mercado Público integration and
  retrieval. Independently verify `qwen3:1.7b` and
  backend-to-Ollama connectivity; use the selected `bge-m3` model at 1024
  dimensions for embeddings. Hosted API providers are deferred. Use
  private local storage during development; record no tickets or secrets in
  repository files.

#### Step 3: [Cross-cutting] Establish runnable test foundations

- **Requirements**: REQ-001, REQ-002 and NFR-001 through NFR-006
- **Design inputs**: `research.md`, `artifacts/tech-stack.md`
- **Description**: Preserve `python -m pytest` and `npm run build`, add
  PostgreSQL-backed integration-test setup and Playwright browser-test
  configuration, and document the per-capability fallback matrix. Do not make
  browser testing optional merely because Docker is unavailable.

### Phase 2: Foundational Capabilities

#### Step 4: [Cross-cutting] Implement the reviewed relational schema

- **Requirements**: REQ-001, REQ-002, REQ-010 through REQ-024
- **Design inputs**: approved `data-architecture.md`,
  `artifacts/data-model.md`
- **Description**: Add Alembic migrations in dependency/domain slices for the
  approved target entities, including relational roles and permissions.
  Backfill current role values and preserve existing authorization behavior and
  data. The selected pgvector embedding dimension is 1024. Validate
  fresh-database migration and upgrade from the current
  schema.

#### Step 5: [Cross-cutting] Enforce tenant access and audit boundaries

- **Requirements**: REQ-001, REQ-002, REQ-016, REQ-024; NFR-001, NFR-002
- **Design inputs**: existing `backend/app/api/dependencies/`,
  `backend/app/core/permissions.py`, `backend/app/services/`,
  `artifacts/data-model.md`
- **Description**: Reuse authenticated user/company context and backend
  permission checks for every new company-owned query and mutation. Add shared
  audit behavior without allowing client-supplied tenant identifiers to
  authorize access.

#### Step 6: [Cross-cutting] Define provider, source, and storage adapters

- **Requirements**: REQ-003 through REQ-009, REQ-012, REQ-025; NFR-002,
  NFR-004, NFR-005
- **Design inputs**: `research.md`, `research/mercado-publico-api.md`,
  `artifacts/tech-stack.md`
- **Description**: Define typed server-side boundaries for procurement source,
  chat/embedding providers, and private storage. Standardize timeout, error,
  provenance, secret redaction, and deterministic test behavior. Do not invent
  an attachment API or expose provider credentials to the browser.

#### Step 7: [Cross-cutting] Add durable background processing

- **Requirements**: REQ-014, REQ-017, REQ-025; NFR-003, NFR-004
- **Design inputs**: `backend/app/workers/main.py`,
  `assessment/engines/facts/data-architecture.md`
- **Description**: Use persisted job/run states with retry-safe processing and
  the existing worker container. Start without a broker; revisit only if a
  concrete reliability or scale requirement emerges.

#### Step 8: [Cross-cutting] Connect product routes and browser verification

- **Requirements**: REQ-001, REQ-002, REQ-008, REQ-011; NFR-001, NFR-002
- **Design inputs**: `frontend/src/app/router/AppRouter.tsx`,
  `frontend/src/lib/api/`, `artifacts/project-structure.md`
- **Description**: Replace relevant placeholder routes with feature pages using
  the existing API client, authenticated shell, and role/permission patterns.
  Add reusable browser auth helpers and a test-only data setup path.

### Phase 3: User Story 1 — Find and Follow an Opportunity (P1)

#### Step 9: [US1] Integrate the official opportunity source

- **Requirements**: REQ-008, REQ-009
- **Design inputs**: `research/mercado-publico-api.md`, Step 2 validation results
- **Description**: Implement and contract-test the source adapter using only
  verified request and response shapes. If the official service or ticket is
  unavailable, keep integration visibly unavailable and do not fabricate
  results.

#### Step 10: [US1] Persist shared opportunities and company tracking

- **Requirements**: REQ-001, REQ-002, REQ-010
- **Design inputs**: approved `data-architecture.md`
- **Description**: Store source facts in the shared catalogue and company state
  in tenant-owned tracking records. Preserve source identifiers and freshness;
  enforce one tracking record per opportunity and company.

#### Step 11: [US1] Deliver search, follow, and isolation flows

- **Requirements**: REQ-001, REQ-002, REQ-008, REQ-009, REQ-010
- **Design inputs**: US1 API/UI contracts and existing authenticated routes
- **Description**: Add authorized search/list/detail/follow actions and the
  tender pages. Preserve access to already tracked items during source outage.

### Phase 4: User Story 2 — Configure and Choose an Ollama Model (P1)

#### Step 12: [US2] Implement the Ollama provider adapter

- **Requirements**: REQ-003, REQ-007
- **Design inputs**: recorded provider decision from Step 2
- **Description**: Implement the Ollama client and provider registry behind a
  server-side boundary. Hosted API clients are a later extension. Keep Ollama
  endpoint settings server-side and surface connection/model errors explicitly.

#### Step 13: [US2] Enforce company model policies and separate embeddings

- **Requirements**: REQ-004, REQ-005, REQ-006
- **Design inputs**: approved AI model/policy schema and embedding decision
- **Description**: Add company enable/disable and default policies, user chat
  preference, capability validation, and an invariant that chat model changes
  do not alter existing vectors.

#### Step 14: [US2] Deliver model settings and selection UI

- **Requirements**: REQ-004, REQ-005, REQ-006, REQ-007
- **Design inputs**: backend model-policy contract
- **Description**: Add company-admin controls and a user selector limited to
  server-approved models; verify policy rejection by bypassing the UI.

### Phase 5: User Story 3 — Add and Process Tender Documents (P1)

#### Step 15: [US3] Implement private upload and document versioning

- **Requirements**: REQ-013, REQ-016, REQ-024; NFR-004, NFR-006
- **Design inputs**: approved storage and document schema
- **Description**: Validate supported PDF/DOCX uploads, store bytes privately,
  create versions, retain provenance, and associate files only with authorized
  company tracking records.

#### Step 16: [US3] Add conditional source-document retrieval

- **Requirements**: REQ-012, REQ-025; NFR-004
- **Design inputs**: Step 2 ticket and attachment verification
- **Description**: Implement official-source retrieval only for confirmed
  document links and behavior. Reject arbitrary user-provided server-side URLs;
  provide manual upload when source documents are absent or retrieval fails.

#### Step 17: [US3] Extract text, chunk, and process documents durably

- **Requirements**: REQ-014, REQ-015, REQ-016; NFR-003, NFR-004, NFR-006
- **Design inputs**: approved embedding model/dimension and job design
- **Description**: Process PDF/DOCX versions through the worker, retain
  page/location provenance for chunks, persist processing status, and make
  retries safe without duplicating successful outputs.

#### Step 18: [US3] Deliver document management and status UI

- **Requirements**: REQ-012 through REQ-016, REQ-025
- **Design inputs**: document API contracts and job states
- **Description**: Add upload/source-document actions, version history, processing
  state, actionable failures, and retry controls for authorized users.

### Phase 6: User Story 4 — Review Traceable Go/No-Go Analysis (P1)

#### Step 19: [US4] Run deterministic checks and AI-assisted analysis

- **Requirements**: REQ-017, REQ-018, REQ-019; NFR-002, NFR-003
- **Design inputs**: approved analysis schema, selected model/provider, source
  documents
- **Description**: Create durable analysis runs; compute hard dates and rules
  deterministically; use the approved model for bounded extraction/classification;
  expose progress, completion, and failure.

#### Step 20: [US4] Persist findings, evidence, and reproducibility data

- **Requirements**: REQ-018, REQ-019; NFR-006
- **Design inputs**: approved analysis/evidence schema
- **Description**: Store compliant, non-compliant, or unverified classifications,
  risks, deadlines, missing evidence, model/ruleset version, and exact document
  versions/locations used.

#### Step 21: [US4] Record human decisions and show the report

- **Requirements**: REQ-018, REQ-020, REQ-024
- **Design inputs**: analysis API and audit conventions
- **Description**: Keep reviewer decision/reason separate from AI output, enforce
  server permission, audit the decision, and display citations and uncertainty.

### Phase 7: User Story 5 — Track the Opportunity Lifecycle (P1)

#### Step 22: [US5] Implement internal status, owner, milestones, and history

- **Requirements**: REQ-011, REQ-024
- **Design inputs**: approved tracking event/milestone schema
- **Description**: Support authorized updates, assignment, notes, milestone
  sources, and attributable history without modifying shared public source facts.

#### Step 23: [US5] Deliver lifecycle detail and permission behavior

- **Requirements**: REQ-001, REQ-002, REQ-011, REQ-024; NFR-001
- **Design inputs**: tracking API contracts and current route guards
- **Description**: Add the tracked-tender detail/timeline UI and verify that
  unauthorized/cross-company changes fail at the API boundary.

### Phase 8: User Story 6 — Ask Grounded Questions in Context (P2)

#### Step 24: [US6] Implement tenant-scoped conversations and retrieval

- **Requirements**: REQ-016, REQ-021, REQ-022; NFR-001, NFR-006
- **Design inputs**: approved conversation, chunk, citation, and embedding schemas
- **Description**: Scope retrieval by company and optional tracked tender; persist
  messages and citations to the exact source version/location; return no
  unsupported factual answer when evidence is absent.

#### Step 25: [US6] Deliver chat endpoint and provider-aware UI

- **Requirements**: REQ-005, REQ-007, REQ-021, REQ-022; NFR-002
- **Design inputs**: provider policy API and retrieval contract
- **Description**: Use only company-approved chat models, return explicit provider
  errors, and render evidence citations and missing-evidence responses.

### Phase 9: User Story 7 — Prepare a Versioned Offer Package (P3)

#### Step 26: [US7] Create offer versions, checklist, and selected documents

- **Requirements**: REQ-016, REQ-023, REQ-024; NFR-006
- **Design inputs**: approved offer/document relation schema
- **Description**: Associate offers with a company's tracked tender, preserve
  versioned checklist state, and reference only selected authorized document
  versions.

#### Step 27: [US7] Generate and deliver the offer package

- **Requirements**: REQ-016, REQ-023, REQ-024; NFR-001, NFR-004
- **Design inputs**: private storage and offer API contracts
- **Description**: Generate a versioned downloadable package, audit the action,
  and verify it contains no files outside the owning company's authorized scope.

### Phase 10: Polish and Cross-Cutting Delivery

#### Step 28: [Cross-cutting] Complete regression, operations, and documentation

- **Requirements**: REQ-001 through REQ-025; NFR-001 through NFR-006
- **Design inputs**: all feature contracts and quality gates
- **Description**: Run all module, PostgreSQL migration, API, and browser journeys;
  update README/setup/credential guidance for the new services and job flow;
  rehearse fresh and existing database startup.

#### Step 29: [Cross-cutting] Automate CI quality checks

- **Requirements**: REQ-001, REQ-002, REQ-024; NFR-001 through NFR-006
- **Design inputs**: current backend/frontend commands and approved test strategy
- **Description**: Add a CI workflow that runs backend tests, frontend typecheck
  and build, migration checks, and browser tests where the runner supports
  Chromium; a browser-install failure must be recorded and cannot be silently
  skipped. Production CD is a separate decision because no cloud target has
  been selected.

## Task Breakdown

Tests for each implementation slice are written first and must fail for the
intended reason before implementation begins. After each implementation task,
run its module-level tests and record command, exit code, and pass/fail/skip
counts.

### Phase 1: Setup and Approval Gates

- [x] T001 [Plan:1.1] Finalize field constraints, ownership, retention, and role backfill for the approved planning baseline in `../assessment/engines/facts/data-architecture.md`; preserve current permission behavior.
- [ ] T002 [Plan:1.2] Validate official Mercado Público availability, list/detail responses, terms, limits, and document links when a ticket is available; until then record the live-integration blocker in `research/mercado-publico-api.md` without storing the ticket, and proceed with independent tasks.
- [x] T003 [Plan:1.2] Verify `qwen3:1.7b` and backend-to-Ollama connectivity, select `bge-m3` at 1024 dimensions, and record local private storage in `research.md`; hosted APIs remain deferred.
- [x] T004 [Plan:1.3] Add PostgreSQL integration-test configuration and Playwright scripts/configuration in `backend/app/tests/conftest.py`, `frontend/package.json`, and `frontend/playwright.config.ts`.

### Phase 2: Foundational Capabilities

- [x] T005 [Plan:2.1] Add migration tests for fresh install and upgrade from the current schema in `backend/app/tests/test_migrations.py`.
- [x] T006 [Plan:2.1] Implement approved additive Alembic migrations for product entities and relational roles/permissions in `backend/alembic/versions/`; backfill existing role values and preserve identity/access behavior.
- [x] T007 [Plan:2.2] Add two-company read/write denial tests for all new protected domains in `backend/app/tests/test_tenant_isolation.py`.
- [x] T008 [Plan:2.2] Implement reusable authenticated-company scoping and audit helpers in `backend/app/api/dependencies/`, `backend/app/services/`, and `backend/app/services/audit_service.py`.
- [x] T009 [Plan:2.3] Add deterministic mock-contract tests for procurement, AI-provider, and storage adapter failures in `backend/app/tests/test_external_contracts.py`.
- [x] T010 [Plan:2.3] Define typed provider/source/storage interfaces, server-side settings, timeouts, and secret redaction in `backend/app/integrations/` and `backend/app/core/config.py`.
- [x] T011 [Plan:2.4] Add durable job lifecycle, idempotent retry, and failure-state tests in `backend/app/tests/test_processing_jobs.py`.
- [x] T012 [Plan:2.4] Implement persisted job claiming/status/retry behavior and worker execution in `backend/app/models/`, `backend/app/services/`, and `backend/app/workers/main.py`.
- [x] T013 [Plan:2.5] Add reusable browser login, authorization, and isolated test-data helpers in `frontend/e2e/`.
- [x] T014 [Plan:2.5] Add protected product-route shells and feature navigation using the shared API client in `frontend/src/app/router/AppRouter.tsx` and `frontend/src/features/`.

### Phase 3: User Story 1 — Find and Follow an Opportunity

- [ ] T015 [Plan:3.1] Write source-adapter fixture tests for documented searches, detail-by-code, malformed responses, timeout, and unavailable service in `backend/app/tests/test_market_public_adapter.py`.
- [ ] T016 [Plan:3.1] Implement the verified Mercado Público client, ticket redaction, and source mapping in `backend/app/integrations/procurement/mercado_publico.py`.
- [ ] T017 [Plan:3.2] Write catalogue deduplication and same-/cross-company tracking tests in `backend/app/tests/test_tender_catalog.py`.
- [ ] T018 [Plan:3.2] Implement shared opportunity persistence and company-scoped tracking operations in `backend/app/models/`, `backend/app/repositories/`, and `backend/app/services/tender_service.py`.
- [ ] T019 [Plan:3.3] Write API authorization, search, follow, source-outage, and duplicate-follow tests in `backend/app/tests/test_tender_api.py`.
- [ ] T020 [Plan:3.3] Implement tender search/detail/follow APIs and pages in `backend/app/api/v1/tenders.py` and `frontend/src/features/tenders/`.

### Phase 4: User Story 2 — Configure and Choose an Ollama Model

- [ ] T021 [Plan:4.1] Write Ollama adapter tests for reachable/unreachable service, unavailable model, and timeout behavior in `backend/app/tests/test_ai_providers.py`.
- [ ] T022 [Plan:4.1] Implement the Ollama client and replaceable server-side provider registry in `backend/app/integrations/ai/`.
- [ ] T023 [Plan:4.2] Write company allow-list, default-model, user-preference, and embedding-separation tests in `backend/app/tests/test_ai_model_policy.py`.
- [ ] T024 [Plan:4.2] Implement model capability metadata, company policies, user preference persistence, and dimension validation in `backend/app/models/`, `backend/app/services/ai_model_service.py`, and `backend/app/api/v1/ai_models.py`.
- [ ] T025 [Plan:4.3] Write browser tests for admin model settings, user selection, and rejected disabled models in `frontend/e2e/ai-models.spec.ts`.
- [ ] T026 [Plan:4.3] Implement model settings and selector pages in `frontend/src/features/settings/` and `frontend/src/features/ai/`.

### Phase 5: User Story 3 — Add and Process Tender Documents

- [ ] T027 [Plan:5.1] Write upload validation, company isolation, version, and private-access tests in `backend/app/tests/test_document_uploads.py`.
- [ ] T028 [Plan:5.1] Implement private storage, upload validation, document metadata, and version services in `backend/app/integrations/storage/`, `backend/app/models/`, and `backend/app/services/document_service.py`.
- [ ] T029 [Plan:5.2] Write source-document retrieval contract tests using only the verified official link behavior in `backend/app/tests/test_source_documents.py`.
- [ ] T030 [Plan:5.2] Implement conditional source-document retrieval and manual-upload fallback in `backend/app/integrations/procurement/` and `backend/app/services/document_service.py`.
- [ ] T031 [Plan:5.3] Write PDF/DOCX extraction, page/location provenance, retry, and duplicate-output tests in `backend/app/tests/test_document_processing.py`.
- [ ] T032 [Plan:5.3] Implement extraction, chunking, approved embeddings, and durable processing states in `backend/app/integrations/extraction/`, `backend/app/integrations/ai/`, and `backend/app/workers/`.
- [ ] T033 [Plan:5.4] Write browser tests for upload, processing status, failure, and retry in `frontend/e2e/documents.spec.ts`.
- [ ] T034 [Plan:5.4] Implement document management, version, source, status, and retry UI in `frontend/src/features/documents/`.

### Phase 6: User Story 4 — Review Traceable Go/No-Go Analysis

- [ ] T035 [Plan:6.1] Write analysis lifecycle, deterministic deadline/rule, and explicit failure tests in `backend/app/tests/test_analysis_runs.py`.
- [ ] T036 [Plan:6.1] Implement analysis run orchestration and deterministic checks in `backend/app/services/analysis_service.py` and `backend/app/workers/`.
- [ ] T037 [Plan:6.2] Write finding classification, source-version citation, missing-evidence, and reproducibility tests in `backend/app/tests/test_analysis_evidence.py`.
- [ ] T038 [Plan:6.2] Implement versioned findings/evidence/model/ruleset persistence and report construction in `backend/app/models/`, `backend/app/services/analysis_service.py`, and `backend/app/schemas/`.
- [ ] T039 [Plan:6.3] Write reviewer authorization, separate-decision, and audit tests in `backend/app/tests/test_analysis_decisions.py`.
- [ ] T040 [Plan:6.3] Implement decision APIs, audit events, and report/review pages in `backend/app/api/v1/analysis.py` and `frontend/src/features/analysis/`.

### Phase 7: User Story 5 — Track the Opportunity Lifecycle

- [ ] T041 [Plan:7.1] Write status, assignment, milestone, note, and history tests in `backend/app/tests/test_tender_lifecycle.py`.
- [ ] T042 [Plan:7.1] Implement tenant-scoped lifecycle updates and attributable events in `backend/app/services/tender_service.py` and `backend/app/models/`.
- [ ] T043 [Plan:7.2] Write browser/API tests for lifecycle permissions and timeline visibility in `frontend/e2e/tender-lifecycle.spec.ts` and `backend/app/tests/test_tender_lifecycle_api.py`.
- [ ] T044 [Plan:7.2] Implement tracked-tender detail, assignment, milestone, and history UI in `frontend/src/features/tenders/`.

### Phase 8: User Story 6 — Ask Grounded Questions in Context

- [ ] T045 [Plan:8.1] Write retrieval scope, citation location, and insufficient-evidence tests in `backend/app/tests/test_conversations.py`.
- [ ] T046 [Plan:8.1] Implement company/tender-scoped conversations, retrieval, message persistence, and citations in `backend/app/services/chat_service.py` and `backend/app/models/`.
- [ ] T047 [Plan:8.2] Write provider failure, model-policy, and citation rendering tests in `backend/app/tests/test_chat_api.py` and `frontend/e2e/chat.spec.ts`.
- [ ] T048 [Plan:8.2] Implement chat APIs and contextual chat/model-selection UI in `backend/app/api/v1/chat.py` and `frontend/src/features/chat/`.

### Phase 9: User Story 7 — Prepare a Versioned Offer Package

- [ ] T049 [Plan:9.1] Write offer ownership, checklist, selected-version, and version-history tests in `backend/app/tests/test_offers.py`.
- [ ] T050 [Plan:9.1] Implement offer/version/checklist/document associations in `backend/app/models/` and `backend/app/services/offer_service.py`.
- [ ] T051 [Plan:9.2] Write generated-package contents, authorization, and audit tests in `backend/app/tests/test_offer_packages.py`.
- [ ] T052 [Plan:9.2] Implement package generation/download APIs and offer UI in `backend/app/api/v1/offers.py` and `frontend/src/features/offers/`.

### Phase 10: Polish and Cross-Cutting Delivery

- [ ] T053 [Plan:10.1] Add full-flow browser journeys for search/follow, document processing, analysis review, grounded chat, and offer download in `frontend/e2e/`.
- [ ] T054 [Plan:10.1] Update `README.md`, `GUIA_PROYECTO.md`, and `docker-compose.yml` for worker, storage, provider configuration, migrations, and local startup without credentials.
- [ ] T055 [Plan:10.2] Add CI jobs for backend tests, frontend build, migration validation, and Playwright in `.github/workflows/ci.yml`.
- [ ] T056 [Plan:10.2] Verify CI artifact/log redaction, PostgreSQL service health, browser installation, and failure exit codes in `.github/workflows/ci.yml`.

## Project Structure

```text
backend/app/
  api/v1/                 # feature routes using existing auth/permission dependencies
  core/                   # config, errors, security, permission policy
  integrations/
    ai/                   # Ollama provider adapter initially; hosted later
    procurement/          # official Mercado Público adapter
    extraction/           # PDF/DOCX extraction
    storage/              # private local adapter initially; cloud adapter later
  models/                 # SQLAlchemy entities
  schemas/                # request/response contracts
  services/               # domain operations and tenant-scoped workflows
  workers/                # durable document/analysis job execution
backend/alembic/versions/ # additive, domain-sliced migrations
backend/app/tests/        # pytest unit/API tests; PostgreSQL integration tests
frontend/src/features/    # tenders, documents, settings, analysis, chat, offers
frontend/src/lib/          # shared API client, auth, and typed feature contracts
frontend/e2e/              # Playwright user journeys
.github/workflows/         # CI checks; production deploy workflow deferred
```

Final names and module boundaries remain design decisions until the approved
schema and implementation sequencing are reviewed.

## Testing Strategy

### appType

Mixed application: FastAPI JSON API plus React single-page application with
client-side routing.

### Critical User Journeys

1. Authenticated company user searches, follows an opportunity, and cannot see
   another company's tracking state.
2. User uploads a document, sees durable processing state, and reads an
   actionable failure/retry result.
3. User runs an analysis and reviews source-version citations and a separate
   human decision.
4. User asks a tender-scoped chat question and receives supported citations or
   an explicit insufficient-evidence response.
5. User creates and downloads an offer version containing only authorized
   selected documents.

### primaryValidationStack

- Backend API/integration: pytest + httpx against FastAPI; PostgreSQL 16 with
  pgvector through Docker Compose for database/migration fidelity.
- Browser E2E: Playwright against the running React and FastAPI applications.
- External services: deterministic HTTP transports/fixtures for Mercado Público
  and AI providers; never depend on live provider availability for CI.
- File storage: temporary local private-storage adapter in tests; test a
  production object-storage adapter against a configured bucket only after its
  provider is selected for deployment.
- Build: `python -m pytest` in `backend/`; `npm run build` and Playwright tests
  in `frontend/`.

### fallbackMatrix

- `infra-tier`: Docker Compose with PostgreSQL 16/pgvector -> SQLite/in-memory
  and mocked external services only if `docker info` fails. Gap: SQLite does not
  validate PostgreSQL JSONB, vector extension/dimensions, PostgreSQL constraints,
  or production migration behavior. Do not mark the PostgreSQL migration gate
  passed from SQLite results.
- `browser-tier`: Playwright Chromium -> framework-native API tests only if the
  specific Playwright/browser installation fails with recorded evidence. Gap:
  no verification of route rendering, browser auth state, downloads, or UI
  behavior.

These are independent capability axes. Docker unavailability must not be used
to skip Playwright when Node/browser installation succeeds.

### Environment Requirements

- Python 3.12-compatible backend environment and Node.js.
- Functional Docker daemon for PostgreSQL 16/pgvector integration.
- Playwright and Chromium browser binaries for browser E2E.
- Outbound HTTPS during setup for package/browser retrieval and any optional
  live API smoke check.
- A valid Mercado Público ticket is required only for a separately controlled
  live smoke test; CI uses fixtures and must not store the ticket.

At planning time, Node.js `v22.13.1` was available, Docker daemon was
unavailable, and Playwright was not installed. Re-check each capability when
execution begins.

### Test Data Strategy

- Create companies, users, tenders, documents, runs, and offers with unique UUIDs
  in each test.
- Create two companies in all tenant-isolation suites and attempt both reads and
  writes across the boundary.
- Use transaction rollback or explicit teardown for database rows and temporary
  file storage; do not rely on the demo seed in feature tests.
- Use fixed API/provider fixtures with valid/invalid, timeout, empty, malformed,
  and rate-limited responses.

### Acceptance Criteria

- Every protected feature has automated positive and negative authorization
  coverage, including cross-company access attempts.
- Every source-backed conclusion and citation resolves to the persisted source
  version and location.
- All long-running jobs expose queued/processing/completed/failed states and
  retries do not duplicate completed outputs.
- Fresh migration and upgrade-from-current-schema both pass on PostgreSQL.
- All five browser journeys pass without relying on live AI or Mercado Público
  services.
- Backend pytest, frontend build, migration checks, and configured Playwright
  suite exit with code 0; any fallback and its gaps are reported.

### Validation Review Expectations

For each implementation task, run the module tests and record command,
exit-code, pass/fail/skip counts, and evidence path. Reviewers verify both
independent infrastructure/browser capability axes, migration results, tenant
isolation, provider/source error paths, and no secret-bearing logs or artifacts.

### Legacy Test Assets

- Existing backend pytest suite: discovered; keep and extend. Baseline is 53
  passing tests.
- Existing frontend browser/E2E suite: none found.
- Migration decision: keep existing backend tests; add Playwright for the new
  user journeys. No existing browser tests to rewrite or discard.

## Complexity Tracking

No constitutional exception is planned. The approach retains the modular
monolith and existing PostgreSQL/React stack, adds a worker using the existing
container boundary, and defers a broker and production deployment platform.

## Requirement Mapping

| REQ ID | Description | Plan Items | Implementation Evidence |
|---|---|---|---|
| REQ-001 | Existing authenticated identity/company is access authority | 1.1, 2.1, 2.2, 2.5, 3.2, 3.3, 7.2 | `backend/app/api/dependencies/`, new tenant-scoped services and tests |
| REQ-002 | Server-side authorization for all new operations | 1.1, 2.2, 2.5, 3.3, 7.2 | new API permission dependencies, feature route tests |
| REQ-003 | Catalog providers/models and capabilities | 1.2, 2.3, 4.1 | `backend/app/integrations/ai/`, model catalog schema/tests |
| REQ-004 | Company model allow-list and defaults | 1.2, 4.2, 4.3 | AI policy model/service/API and settings UI |
| REQ-005 | User selects allowed chat model and model use is recorded | 1.2, 4.2, 4.3, 8.2 | preference API, chat/analysis provenance fields, UI and tests |
| REQ-006 | Separate chat/embedding choices; prevent incompatible vectors | 1.2, 2.1, 4.2, 4.3 | embedding configuration, dimension constraints, migration/reindex tests |
| REQ-007 | Provider secrets remain server-side and out of logs | 1.2, 2.3, 4.1, 4.3, 8.2 | server configuration, redaction tests, API response tests |
| REQ-008 | Search public opportunities through official integration | 1.2, 3.1, 3.2, 3.3 | Mercado Público adapter, catalogue/search API and tests |
| REQ-009 | Display source, official link, title, buyer, status, dates | 3.1, 3.3 | opportunity mapping contract and frontend list/detail |
| REQ-010 | Shared opportunity facts, private deduplicated tracking | 1.1, 2.1, 3.2, 3.3 | catalogue/tracking migrations and unique-constraint tests |
| REQ-011 | Update internal tracking lifecycle and history | 2.1, 7.1, 7.2 | tracking service/API, milestones, event history UI |
| REQ-012 | Retain source document provenance/metadata | 1.2, 2.3, 5.2 | source-document metadata and provenance tests |
| REQ-013 | Upload PDF/DOCX when source docs unavailable | 2.4, 5.1, 5.4 | upload endpoint, private storage, document UI tests |
| REQ-014 | Version documents and expose processing status/retry | 2.1, 2.4, 5.1, 5.3, 5.4 | job/document version models, worker and UI |
| REQ-015 | Extract text and retrievable fragments with location | 2.1, 2.4, 5.3 | extraction/chunk/embedding pipeline and tests |
| REQ-016 | Restrict files, chunks, retrieval, analysis, chat, packages | 2.1, 2.2, 5.1, 5.3, 8.1, 9.1, 9.2 | tenant-scoped repositories and cross-company tests |
| REQ-017 | Create analysis runs and show lifecycle | 2.4, 6.1 | durable analysis job/run APIs and progress UI |
| REQ-018 | Classify requirements and provide evidence/risks/deadlines | 6.1, 6.2, 6.3 | analysis rules, findings, report and citation tests |
| REQ-019 | Retain model, ruleset, document versions, result, time | 2.1, 6.1, 6.2 | analysis provenance schema/service and repeatability tests |
| REQ-020 | Store human decision separately with identity/reason/time | 2.1, 6.3 | decision entity/API, audit event, reviewer UI |
| REQ-021 | Company/tender-scoped conversations with citations | 2.1, 8.1, 8.2 | conversation/message/citation schema and chat flows |
| REQ-022 | Distinguish missing evidence; do not fabricate citations | 8.1, 8.2 | retrieval response policy and insufficient-evidence tests |
| REQ-023 | Create offers, checklist, selected versions, generated output | 2.1, 9.1, 9.2 | offer schema/services, package generation/download tests |
| REQ-024 | Audit significant business actions without sensitive content | 2.2, 5.1, 6.3, 7.1, 9.1, 9.2 | audit helper, feature events, log-redaction tests |
| REQ-025 | Manual document path and explicit failure if neither works | 1.2, 2.3, 5.2, 5.4 | source/manual fallback behavior and failure-path tests |
