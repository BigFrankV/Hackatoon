# Feature Specification: Licitaciones AI - Procurement, RAG, Analysis, and Offers

> Governed by: `./constitution.md` (v1.0.0, ratified 2026-11-26), with product scope informed by `../../01_especificacion_integral_licitaciones_ai.md`.

**Feature Branch**: `licitaciones-ai-mvp`
**Created**: 2026-11-26
**Status**: Approved planning baseline; implementation gates remain
**Input**: User wants a complete, multi-company workflow from the product core through Mercado Público discovery, document knowledge, AI-assisted tender analysis, and offer preparation. Initial AI provider is local Ollama; hosted API providers are deferred.

## Scope Baseline

- **Discovery method**: Reviewed product scope in `01_especificacion_integral_licitaciones_ai.md`, current-state notes in `README.md` and `GUIA_PROYECTO.md`, the present frontend placeholder routes, the proposed logical data architecture, and the user's confirmed decisions.
- **Total items discovered**: 8 functional capabilities: AI provider selection, public opportunity search, tenant tracking, document intake, document retrieval/RAG, Go/No-Go analysis, contextual chat, and offer preparation.
- **Items in scope**: 8. The login and company identity foundation are retained; they are not rewritten.
- **Explicit decisions already confirmed**:
  - Use the Mercado Público integration with manual document upload as a fallback.
  - Keep public procurement opportunities in a shared catalog and company-specific tracking, analysis, decisions, conversations, and offers in tenant-owned records.
  - Start with local Ollama, using the user's `qwen3:1.7b` model for chat; defer hosted API integrations while retaining a provider boundary.
  - Use Ollama for embeddings with the dedicated `bge-m3` model at 1024 dimensions. Do not assume the chat model is an embedding model.
  - Migrate the current role enum to relational role/permission tables as part of the planned database work, with explicit backfill and preservation of existing access rules.
  - Use private local document storage for development; select a cloud object-storage provider when deployment is defined.
- **Out of scope for this feature**: Replacing the authentication/session behavior, training/fine-tuning foundation models, hosted AI provider integrations in the initial MVP, automatically submitting a tender or offer to Mercado Público, or allowing an AI model to make a binding participation decision without human approval.

---

## User Scenarios & Testing

### User Story 1 - Find and follow an opportunity (Priority: P1)

As a company user, I want to search public procurement opportunities, review their source information, and add relevant ones to my company's workspace so that my team can evaluate and track them.

**Why this priority**: This establishes the product's main entry point and connects public information with a company's private workflow.

**Independent Test**: Search a known opportunity, open its official source, add it to one demo company, and verify another company cannot see that company's tracking state.

**Acceptance Scenarios**:

1. **Given** a company user with permission to view opportunities, **When** they search using supported criteria, **Then** they see matching public opportunities with source, title, buyer, status, relevant dates, and an official source link.
2. **Given** an opportunity exists in the public catalog, **When** a user follows it, **Then** the system creates one company-specific tracking record and does not create a duplicate when the same company follows it again.
3. **Given** the external source is unavailable, **When** a user opens the opportunities module, **Then** the system explains the source is unavailable and preserves access to already tracked opportunities.

### User Story 2 - Configure and choose an Ollama model (Priority: P1)

As a company administrator, I want to allow approved local Ollama models and set company defaults; as an authorized user, I want to choose an allowed chat model. Hosted API providers can be added in a later phase.

**Why this priority**: Provider flexibility is a core product requirement and must not bypass company policy or document privacy.

**Independent Test**: Configure an available Ollama chat model, select it, and confirm the authorized tender context is used while the stored analysis remains tied to the model that produced it.

**Acceptance Scenarios**:

1. **Given** a company has permitted an Ollama chat model, **When** a user chooses it, **Then** their preference is saved and used for subsequent chat or analysis requests where applicable.
2. **Given** a model is disabled or not permitted for the user's company, **When** the user attempts to select it or send a request using it, **Then** the server rejects the request and identifies an actionable error.
3. **Given** an embedding model is already used to index company documents, **When** a chat model preference changes, **Then** the existing embeddings remain unchanged.

### User Story 3 - Add and process tender documents (Priority: P1)

As a company user, I want the system to retrieve available documents for a tracked opportunity and upload missing documents manually so that the analysis can use the tender's actual bases and annexes.

**Why this priority**: A tender identifier alone is not sufficient evidence for document-based evaluation; the system needs the source documents or user-provided files.

**Independent Test**: Add an official source document and upload a PDF or DOCX fallback, then verify both appear under the correct company's tracked tender with visible processing status.

**Acceptance Scenarios**:

1. **Given** the public source exposes a document, **When** the user requests it for a tracked opportunity, **Then** the document is associated with that company's tracking record and its provenance is retained.
2. **Given** a document is not available from the source, **When** an authorized user uploads a supported file, **Then** it is stored privately, versioned, and associated with the selected tracked opportunity.
3. **Given** processing is running or fails, **When** the user views the document, **Then** they see its current state and a useful error or retry path rather than a false success.

### User Story 4 - Review a traceable Go/No-Go analysis (Priority: P1)

As an authorized company user, I want an analysis that separates verified compliance, non-compliance, and missing evidence, so that I can make an informed decision.

**Why this priority**: This is the product's core decision-support outcome and must be auditable and reviewable.

**Independent Test**: Analyze a tender with known evidence, then verify each finding points to an accessible source document/page or is explicitly marked unverified.

**Acceptance Scenarios**:

1. **Given** a tracked tender has processed documents, **When** an authorized user starts an analysis, **Then** the system records a run and presents progress until it completes or fails.
2. **Given** the analysis completes, **When** the user opens the report, **Then** it includes a recommendation of `GO`, `NO_GO`, or `REVIEW_REQUIRED`, requirements grouped by dimension, risks, deadlines, missing company evidence, and citations where available.
3. **Given** a requirement has no supporting evidence, **When** the report is generated, **Then** it is marked unverified rather than asserted as compliant or non-compliant solely due to missing evidence.
4. **Given** an authorized reviewer confirms or rejects a recommendation, **When** they save the decision and reason, **Then** the decision is recorded separately from the AI output with reviewer and timestamp.

### User Story 5 - Track the opportunity lifecycle (Priority: P1)

As a company team member, I want to manage internal status, owner, milestones, notes, and history for a followed opportunity so that the team can coordinate work through submission or closure.

**Why this priority**: Search identifies opportunities; tracking manages them over time.

**Independent Test**: Change an opportunity's internal state, assign an owner, add a milestone, and verify the activity history records each change.

**Acceptance Scenarios**:

1. **Given** a user can manage a tracked tender, **When** they change its internal status or assignment, **Then** the current state updates and an attributable history event is retained.
2. **Given** a tracked tender has a deadline or custom milestone, **When** the user views its details, **Then** the milestone and source are clearly identifiable.
3. **Given** a user lacks the required company permission, **When** they attempt a restricted update, **Then** the server denies it even if the UI is bypassed.

### User Story 6 - Ask grounded questions in context (Priority: P2)

As an authorized user, I want to ask questions about a selected tender and my company's permitted documents so that I can understand requirements without searching every file manually.

**Why this priority**: Contextual chat builds on secure document processing and citations.

**Independent Test**: Ask a question answered by a known document passage and verify the response cites it; ask about a document in another company and verify it is not retrieved.

**Acceptance Scenarios**:

1. **Given** a user asks a question in a tender conversation, **When** relevant evidence is available, **Then** the answer includes citations to the source document and page.
2. **Given** no relevant evidence is found, **When** the assistant responds, **Then** it states that the available sources do not support an answer and does not invent a citation.
3. **Given** a provider is unavailable, **When** the user submits a question, **Then** the system reports provider failure and does not return a fabricated success response.

### User Story 7 - Prepare a versioned offer package (Priority: P3)

As an authorized user, I want to assemble a checklist and select approved company documents for an offer version so that the team can prepare a traceable submission package.

**Why this priority**: Offer preparation follows the decision to pursue an opportunity and depends on document and tracking foundations.

**Independent Test**: Create an offer for a followed tender, add checklist items and selected document versions, and verify the generated version contains only the selected files.

**Acceptance Scenarios**:

1. **Given** an offer is associated with a tracked tender, **When** a user adds checklist items and document versions, **Then** the selected materials are linked to that offer version and retain their original provenance.
2. **Given** an offer package is generated, **When** the user downloads it, **Then** the package is associated with a version and does not include documents outside the company's authorized scope.

## Edge Cases

- The external source returns no results, times out, is rate-limited, or changes its response format.
- A source opportunity is already in the shared catalog or already tracked by the same company.
- The source lists no downloadable bases, a document link has expired, or an external file cannot be safely retrieved.
- A user uploads an unsupported, corrupt, password-protected, or oversized file.
- A PDF is image-only and requires OCR; extraction may fail or produce incomplete text.
- A model/provider is disabled, temporarily unavailable, rejects a request, or has a different capability than required.
- A company attempts to select a model that is not allowed by its policy.
- A company switches its embedding model after documents have been indexed.
- A document is replaced by a new version while an earlier analysis cites the previous version.
- A user requests evidence from another company or passes a different company identifier in a request.
- A tender has conflicting dates between the public source and a user-entered milestone.
- An analysis is retried, cancelled, or fails after partial processing; previous completed runs and decisions remain intact.
- A user deletes or archives a conversation, document, tender, or offer that is referenced by historical analysis.

## Requirements

### Functional Requirements

- **REQ-001**: The system MUST retain the existing authenticated user and company identity as the authority for access to all new company-owned records.
- **REQ-002**: The system MUST enforce permissions on the server for searching, following, updating, uploading, analyzing, chatting, deciding, and preparing offers.
- **REQ-003**: The system MUST maintain a catalog of configured AI providers and models, including whether each model supports chat, embeddings, or tool use.
- **REQ-004**: A company administrator MUST be able to enable or disable models for that company's use and select company defaults.
- **REQ-005**: An authorized user MUST be able to select a chat model only from the models allowed by their company; the system MUST record the model used for each analysis or assistant response.
- **REQ-006**: The system MUST keep chat-model selection separate from embedding-model selection and MUST not silently mix embeddings from incompatible models.
- **REQ-007**: Provider credentials and private connection details MUST remain server-side and MUST NOT be returned to the frontend or written to application logs.
- **REQ-008**: The system MUST search and display public procurement opportunities through the selected official source integration without treating the external identifier as an authorization credential.
- **REQ-009**: Each displayed public opportunity MUST include its source and official link, and available identifying information such as title, buyer, source status, and important dates.
- **REQ-010**: The system MUST store public opportunity facts separately from each company's private tracking state and MUST prevent duplicate tracking of the same opportunity by the same company.
- **REQ-011**: An authorized company user MUST be able to update internal status, priority, assignment, milestones, and notes for a tracked tender, with an attributable history.
- **REQ-012**: The system MUST retain provenance and fetched metadata for source documents when provided by the official source.
- **REQ-013**: When source documents are unavailable or incomplete, an authorized user MUST be able to upload supported PDF or DOCX files and associate them with a tracked tender.
- **REQ-014**: The system MUST preserve document versions and show processing status, failures, and retry availability.
- **REQ-015**: The system MUST extract document text and create retrievable fragments that retain their source document version and page or other available location.
- **REQ-016**: Every document, fragment, vector search, analysis, citation, and generated package MUST be restricted to the authenticated user's company and authorized tender context.
- **REQ-017**: The system MUST allow an authorized user to create an analysis run and present progress, completion, or failure explicitly.
- **REQ-018**: An analysis MUST classify applicable requirements as compliant, non-compliant, or unverified; provide evidence citations when available; and identify risks, deadlines, and missing company evidence.
- **REQ-019**: An analysis MUST retain its model, prompt/ruleset version, source-document versions, result, and completion time so the result can be interpreted later.
- **REQ-020**: The system MUST store human confirmation or rejection of an analysis recommendation separately, including the responsible user, decision, reason, and time.
- **REQ-021**: The system MUST support conversations scoped to a company and optionally a tracked tender, and answers based on retrieved documents MUST expose citations.
- **REQ-022**: The assistant MUST distinguish unavailable evidence from a negative finding and MUST not claim that a citation supports text it does not contain.
- **REQ-023**: The system MUST allow an authorized user to create an offer for a tracked tender, maintain checklist items, select document versions, and generate versioned output.
- **REQ-024**: Significant administrative, tracking, document, analysis-decision, and offer actions MUST be attributable and auditable without logging secrets or unnecessary document contents.
- **REQ-025**: The system MUST provide a manual document path when public-source retrieval is unavailable, and MUST provide an explicit error when neither source retrieval nor manual upload succeeds.

### Non-Functional Requirements

- **NFR-001**: Tenant isolation MUST be verified by automated tests that attempt cross-company reads and writes for each new data domain.
- **NFR-002**: User-visible errors MUST distinguish source, document processing, provider, authorization, and validation failures without exposing internal stack traces or credentials.
- **NFR-003**: Long-running document and analysis work MUST expose a persistent status and MUST be safely retryable without duplicating completed results.
- **NFR-004**: User-supplied files MUST be validated and stored privately; external document retrieval MUST use the configured source integration rather than arbitrary user-supplied server-side URLs.
- **NFR-005**: The local and cloud environments MUST use the same domain behavior while allowing provider URLs, credentials, storage settings, and database connection details to vary by environment.
- **NFR-006**: The system MUST preserve access to historical analysis evidence after a document is superseded, subject to an explicit retention/deletion policy.

### Key Entities

- **Company, User, Role, Permission**: tenant ownership and authorization.
- **AI Provider, AI Model, Company Model Policy, User AI Preference**: server-configured provider catalog, company allow-list/defaults, and user chat-model selection.
- **Procurement Source, Buyer, Opportunity, Source Document**: shared public source catalog and source provenance.
- **Tracked Tender, Milestone, Tracking Event**: each company's private lifecycle for a shared opportunity.
- **Document Category, Storage Object, Document, Document Version, Extraction, Chunk, Embedding, Processing Job**: private document lifecycle and retrieval artifacts.
- **Analysis Run, Requirement, Finding, Evidence, Decision**: reproducible AI/rules output and human decision.
- **Conversation, Message, Citation**: contextual user interaction and evidence references.
- **Offer, Offer Version, Checklist Item, Offer Document**: versioned proposal package and selected evidence.
- **Audit Log**: attributable security and business events.

## Assumptions

- Mercado Público's current API contract, availability, rate limits, and downloadable-document behavior must be validated before live API integration or source retrieval; this does not block unrelated work such as RBAC, manual uploads, or local AI capabilities.
- A company can track the same public opportunity once; different companies can track the same public opportunity independently.
- PDF and DOCX are the first supported manual document formats, matching the existing product specification.
- Company administrators control the approved model list and defaults. Individual users may choose an allowed chat model. Embedding model changes are company-controlled and require a planned reindex.
- The initial MVP uses local Ollama; hosted API providers are deferred. The provider interface remains replaceable so a later phase can add hosted services.
- Ollama is the initial embedding provider; `bge-m3` at 1024 dimensions is selected for the vector schema.
- The user's `qwen3:1.7b` is the initial chat-model choice as reported by the user; its local installation and backend reachability must be verified before runtime use.
- Development documents use private local storage. A production object-storage provider is deferred until the cloud deployment target is selected.
- Ollama is usable only when the backend can securely reach the Ollama service. A cloud backend does not automatically connect to Ollama installed on an end user's personal computer.
- Preserve current login/session behavior and user/company identity. The user selected relational role/permission tables; the migration must explicitly backfill current role values and preserve existing authorization semantics.
- The data architecture and its physical-schema defaults are approved before product migrations. The vector migration uses the selected embedding model and dimension.
- Deletions in the MVP are logical: retain audit records, versions, and historical analysis evidence, with no automatic hard purge. Define physical retention/purge before production.
- No Mercado Público ticket is currently available for live verification; the user must obtain one before implementation of the live source integration.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In a usability test, at least 9 of 10 company users can find a public opportunity and add it to their company's tracked list in under 3 minutes.
- **SC-002**: 100% of attempted cross-company access tests for tracked tenders, documents, chunks, conversations, analyses, and offers are denied.
- **SC-003**: 100% of completed analysis requirements are labeled compliant, non-compliant, or unverified; every evidence-backed result links to a source version and location.
- **SC-004**: Users can change their preference among company-approved chat models, when more than one is configured, without changing the tracked tender, document versions, or previously saved analysis results.
- **SC-005**: For every document job, users can determine whether it is queued, processing, complete, or failed, and failed jobs have an actionable outcome.
- **SC-006**: An opportunity remains trackable when the external source is temporarily unavailable, and users can add missing tender documents manually.
- **SC-007**: An offer package contains exactly the document versions selected for that offer version and is reproducible from its recorded checklist and file links.

## Requirements Quality Checklist

## Requirement ID Coverage
- [x] All requirements use `REQ-XXX` format.
- [x] IDs are unique and sequential.

## Testability
- [x] Functional requirements describe independently verifiable behavior.
- [x] User stories include acceptance scenarios.

## Completeness
- [x] Scope baseline is documented.
- [x] User stories are prioritized P1, P2, and P3.
- [x] Functional requirements cover the eight discovered capabilities.
- [x] Success criteria are measurable and user-focused.

## Constitution Alignment
- [x] Constitution v1.0.0 exists and was ratified on 2026-11-26.
- [x] Multi-company isolation, server-side authorization, human review, and source evidence follow the principles in the existing product specification.

## Open Validation Before Implementation

- Verify the official Mercado Público API contract and document availability before live integration/retrieval; this does not block unrelated work.
- Physical schema defaults, deletion rules, and role backfill are approved; migration tests must verify them before product migrations are applied.
- `bge-m3` at 1024 dimensions is selected and the vector migration is implemented. Verify the complete local ingestion and chat flow against the running Ollama service.
