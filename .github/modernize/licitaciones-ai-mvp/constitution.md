<!--
Sync Impact Report
Version change: 0.1.0 -> 1.0.0 (first user-ratified baseline)
Modified principles: none
Added sections: none; initial constitution sections retained
Removed sections: none; Target Technology Stack omitted because UPGRADE mode was selected
Templates requiring updates: none; plan template provides a Constitution Check and the spec links this constitution
Follow-up TODOs: none
-->

# Licitaciones AI Constitution

## Migration Mode

**Mode**: UPGRADE

**Justification**: Licitaciones AI already has a working identity and multi-company
foundation. New document, procurement, analysis, chat, and offer capabilities will
be added incrementally; replacing the application or rewriting authentication is
not required.

## Core Principles

### I. Tenant Isolation and Server-Side Authorization

Every company-owned read, write, search, file operation, AI retrieval, analysis,
conversation, and offer MUST be authorized on the server using the authenticated
user's company context. Client-provided company identifiers and model output MUST
NOT grant access. Cross-company relationships MUST be rejected or constrained.

### II. Evidence-Grounded, Human-Controlled Decisions

AI output MUST distinguish supported facts from missing or uncertain evidence.
Findings MUST cite an accessible source and location when evidence exists. Rules
that can be determined exactly, including dates, deadlines, and hard eligibility
conditions, MUST be evaluated by deterministic logic. AI recommendations are
advisory; an authorized person records the final participation decision.

### III. Data Integrity, Provenance, and Auditability

Persisted business facts MUST have explicit ownership, stable identifiers,
constraints, and relationships. External data and documents MUST retain source
and retrieval provenance. Analysis results MUST identify the source versions and
rules/model versions used. Significant security and business decisions MUST be
attributable without logging credentials or unnecessary document contents.

### IV. Provider-Neutral Integration and Secret Safety

Chat, embeddings, document extraction, procurement sources, and storage MUST be
accessed through bounded module interfaces so a provider can be changed without
rewriting business rules. Chat-model preferences MUST be limited to models
allowed by the company. Embedding model changes MUST be explicit and MUST NOT
silently mix incompatible vector spaces. Provider credentials MUST stay
server-side and outside source control.

### V. Incremental, Tested, Observable Delivery

Features MUST be delivered in small, independently verifiable vertical slices.
Database changes MUST use reviewed, reversible migrations where feasible and
MUST preserve existing identity data. User-visible errors, background job states,
provider failures, and retry outcomes MUST be explicit; the system MUST NOT
return success-shaped fallbacks. Tests MUST cover permission boundaries,
cross-company isolation, and the behavior introduced by each change.

## Additional Constraints

- Preserve the existing authentication/session behavior unless a separate
  approved requirement demonstrates a necessary change.
- Keep public procurement source facts separate from company-private tracking,
  analysis, notes, and offer data.
- Keep document bytes in private storage: use private local storage during
  development and private object storage in production. Use relational storage
  for ownership, metadata, versions, extracted content references, and workflow
  state.
- Keep provider secrets in local environment configuration during development
  and in a managed secret store in production. Never expose them to the browser.
- Local and cloud environments may use different infrastructure, but must
  preserve the same authorization and domain behavior.
- Do not introduce microservices, a queue broker, or a new persistence platform
  without a concrete scale, reliability, or operational requirement.

## Quality Gates

- Every protected feature has backend authorization tests, including attempts to
  access another company's records.
- Every external integration has explicit timeout/error behavior and a
  deterministic test path that does not depend on the live provider.
- Document ingestion and analysis expose durable states and can be safely
  retried without duplicating successful results.
- Every analysis requirement is represented as compliant, non-compliant, or
  unverified; supported conclusions retain traceable evidence.
- Database migrations are reviewed against the approved logical data model and
  validated against both a fresh database and an existing development database
  before use.
- Documentation and configuration examples MUST describe the implemented
  behavior and MUST NOT contain real credentials.

## Governance

This constitution governs feature specifications, implementation plans, code
changes, and reviews for Licitaciones AI. Amendments require a documented reason,
an increment to the semantic version, and review of affected requirements,
plans, migrations, and operational documentation. MAJOR changes redefine or
remove a binding principle; MINOR changes add or materially expand a principle;
PATCH changes clarify wording without changing obligations.

Each feature plan MUST identify the principles it satisfies and provide
verification evidence for applicable quality gates. A reviewer MUST flag
unresolved deviations before implementation; any accepted exception must state
its scope, reason, owner, and review point.

**Version**: 1.0.0 | **Ratified**: 2026-11-26 | **Last Amended**: 2026-11-26
