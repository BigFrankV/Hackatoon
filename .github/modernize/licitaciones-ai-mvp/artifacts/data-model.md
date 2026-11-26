# Existing Data Model

This document records the schema currently implemented. The approved target
model is documented in
[`data-architecture.md`](../../assessment/engines/facts/data-architecture.md),
including product tables created by Alembic revisions `0003` through `0006`.

## Persistence

PostgreSQL is accessed through SQLAlchemy `AsyncSession`. Alembic owns schema
changes. Services explicitly call `commit()` and, for integrity failures,
`rollback()`; no repository abstraction or application-wide transaction wrapper
was found.

## Implemented Entities

### `companies`

Fields: UUID `id`; required `legal_name`; optional `display_name`, `tax_id`,
`email`, `phone`, and `address`; `status`; timestamps `created_at` and
`updated_at`; optional `deactivated_at`.

`tax_id` is unique when set. A company has many users.

### `users`

Fields: UUID `id`; optional `company_id`; required `role_id` and `role_scope`;
unique required `email`; required `first_name`, `last_name`, and `password_hash`;
enum `status`;
`must_change_password`; `failed_login_attempts`; optional `locked_until`,
`last_login_at`, and `deactivated_at`; timestamps.

Each user has one role through `role_id`. The composite foreign key to
`roles(id, scope)` and the scope/company check constraint ensure platform roles
have no company and company roles belong to a company. A user belongs to at most
one company and may have many refresh tokens and audit events.

### `roles`, `permissions`, and `role_permissions`

`roles` stores system role codes, names, scopes, and system status.
`permissions` stores stable permission codes and descriptions.
`role_permissions` is the many-to-many grant table with a composite primary key.
Migration `0002_relational_rbac` seeds the existing three role codes and
permission grants, then backfills each user's `role_id` and `role_scope` without
changing their identity or password data. Runtime authorization reads grants
from these relations.

### `refresh_tokens`

Fields: UUID `id`, `user_id`, and `family_id`; unique `token_hash`; timestamps
`created_at` and `expires_at`; optional `revoked_at`, `replaced_by_id`,
`user_agent`, `ip_address`, and `reuse_detected_at`.

Each token belongs to one user. `replaced_by_id` is a self-reference. The raw
refresh token is not persisted.

### `audit_logs`

Fields: UUID `id`; optional `actor_user_id` and `company_id`; required `action`
and `entity_type`; optional string `entity_id`; `occurred_at`; optional
`ip_address`, `user_agent`, and `metadata` (JSONB on PostgreSQL).

Actor and company references use `SET NULL` on deletion. The generic
`entity_type`/`entity_id` pair is not a foreign key.

## Relationships

- `companies 1 -> many users`
- `roles 1 -> many users`
- `roles many <-> many permissions` through `role_permissions`
- `users 1 -> many refresh_tokens`
- `refresh_tokens 0..1 -> 0..1 refresh_tokens` through `replaced_by_id`
- `users 1 -> many audit_logs` as actor
- `companies 1 -> many audit_logs`

## Not Yet Implemented

The non-vector product tables are created by revisions `0003` through `0005`;
revision `0006` adds product permissions and durable worker lease metadata and
is applied to the local PostgreSQL database. The
`document_processing_jobs` ORM mapping and lifecycle service are implemented,
including lease recovery and idempotent retries. Tenant-scoped query/audit
helpers and cross-company checks for tracked tenders, documents, jobs,
analyses, conversations, and offers are implemented. The remaining product
ORM mappings, feature services, and APIs belong to later phases.
`document_embeddings` and pgvector indexes are intentionally absent until the
embedding model and dimension are selected.
