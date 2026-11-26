# Architecture Index

## Scope and Status

This focused index captures only the current architecture needed to plan the
Licitaciones AI MVP. It is not an exhaustive source-anchored inventory of every
existing API endpoint and frontend page. Authentication and multi-company
identity are treated as existing integration foundations; new product domains
have no implementation units yet.

This index is not the full contract. Do not implement from this file alone;
follow the artifact paths below.

## Global Artifacts

- [`project-structure.md`](./project-structure.md)
  - Who reads: planning and implementation.
  - Use for: application boundaries, current layers, entry points, implemented
    and placeholder domains.
- [`tech-stack.md`](./tech-stack.md)
  - Who reads: planning and implementation.
  - Use for: declared runtimes, frameworks, dependencies, and present
    integration gaps.
- [`data-model.md`](./data-model.md)
  - Who reads: planning, schema review, and implementation.
  - Use for: current persisted entities and relationships only.
- [`data-architecture.md`](../../assessment/engines/facts/data-architecture.md)
  - Who reads: planning and database implementation.
  - Use for: normalized target model accepted as the planning baseline; it is
    not the current schema or an approved migration.
- [`spec.md`](../spec.md)
  - Who reads: all feature work.
  - Use for: user journeys, requirements, boundaries, and confirmed decisions.
- [`constitution.md`](../constitution.md)
  - Who reads: planning and review.
  - Use for: ratified project governance, version 1.0.0.
- [`mercado-publico-api.md`](../research/mercado-publico-api.md)
  - Who reads: procurement integration planning.
  - Use for: facts verified from the official API information page and open
    questions that still gate implementation.

## Existing Integration Contracts to Preserve

- Backend routes depend on authenticated user context and backend permission
  checks; do not treat frontend route guards as authorization.
- New company-owned data must use the authenticated user's company context.
  The client must not choose an arbitrary tenant boundary.
- Frontend requests use the shared API client, bearer access token, cookie
  credentials, and the configured API base URL.
- Existing login and refresh behavior are retained by the feature scope; no
  authentication rewrite is implied.
- The worker has no current job contract; a background-processing design must be
  made explicitly in the implementation plan.

## Candidate Planning Slices

These are requirement groupings from the feature specification, not committed
code-unit boundaries or sequencing decisions:

1. Mercado Público discovery and shared opportunity catalogue.
2. Company-private tender tracking and workflow state.
3. AI provider/model policy, including Ollama reachability and server-side
   configuration (hosted APIs are deferred from the initial MVP).
4. Manual document intake, private storage, and durable processing state.
5. Text extraction, chunking, embeddings, and tenant-scoped retrieval.
6. Evidence-linked Go/No-Go analysis with deterministic rules and human
   decisions.
7. Company-scoped contextual chat and citations.
8. Offer drafts, versions, checklist, and generated artifacts.

Use the `REQ-XXX` IDs in `spec.md` to assign these requirements during planning.
Do not treat this list as a final target module count.

## Required Completion Evidence

Before database migrations, the plan must identify the final schema and role
backfill. Detail-by-code has been verified against the live Mercado Público API.
Before expanding to list search, tracking, or document retrieval, verify API
availability and the document contract; that ticket/API gate does not block
unrelated implementation. The plan must also identify the
authentication/company integration points, worker/job behavior, and
verification evidence required for each requirement. Tests must include
cross-company isolation and AI/provider failure behavior.
