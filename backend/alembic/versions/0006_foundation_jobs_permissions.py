"""Add product permissions and durable worker lease metadata.

Revision ID: 0006_foundation_jobs_permissions
Revises: 0005_analysis_chat_offers
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_foundation_jobs_permissions"
down_revision: str | Sequence[str] | None = "0005_analysis_chat_offers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PRODUCT_PERMISSION_GRANTS = {
    "tenders.read": ("admin", "user"),
    "tenders.manage": ("admin", "user"),
    "documents.read": ("admin", "user"),
    "documents.manage": ("admin", "user"),
    "analysis.read": ("admin", "user"),
    "analysis.run": ("admin", "user"),
    "analysis.decide": ("admin", "user"),
    "chat.use": ("admin", "user"),
    "offers.read": ("admin", "user"),
    "offers.manage": ("admin", "user"),
}


def upgrade() -> None:
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )
    role_ids = {
        code: role_id if isinstance(role_id, uuid.UUID) else uuid.UUID(str(role_id))
        for code, role_id in op.get_bind()
        .execute(sa.text("SELECT code, id FROM roles"))
        .all()
    }
    permission_ids = {code: uuid.uuid4() for code in PRODUCT_PERMISSION_GRANTS}
    op.bulk_insert(
        permissions,
        [
            {
                "id": permission_ids[code],
                "code": code,
                "description": code.replace(".", " ").replace("_", " ").title(),
            }
            for code in PRODUCT_PERMISSION_GRANTS
        ],
    )
    op.bulk_insert(
        role_permissions,
        [
            {
                "role_id": role_ids[role_code],
                "permission_id": permission_ids[permission_code],
            }
            for permission_code, role_codes in PRODUCT_PERMISSION_GRANTS.items()
            for role_code in role_codes
        ],
    )

    op.add_column(
        "document_processing_jobs",
        sa.Column("payload", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
    )
    op.add_column(
        "document_processing_jobs",
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "document_processing_jobs",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "document_processing_jobs",
        sa.Column("locked_by", sa.String(120), nullable=True),
    )
    op.add_column(
        "document_processing_jobs",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_document_processing_jobs_lease",
        "document_processing_jobs",
        ["status", "lease_expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_processing_jobs_lease",
        table_name="document_processing_jobs",
    )
    op.drop_column("document_processing_jobs", "updated_at")
    op.drop_column("document_processing_jobs", "locked_by")
    op.drop_column("document_processing_jobs", "lease_expires_at")
    op.drop_column("document_processing_jobs", "locked_at")
    op.drop_column("document_processing_jobs", "payload")

    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("permission_id", sa.Uuid()),
    )
    ids = [
        row[0]
        for row in op.get_bind()
        .execute(
            sa.select(permissions.c.id).where(
                permissions.c.code.in_(PRODUCT_PERMISSION_GRANTS)
            )
        )
        .all()
    ]
    if ids:
        op.execute(role_permissions.delete().where(role_permissions.c.permission_id.in_(ids)))
        op.execute(permissions.delete().where(permissions.c.id.in_(ids)))
