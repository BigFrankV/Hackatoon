"""Move user roles and permissions into relational tables.

Revision ID: 0002_relational_rbac
Revises: 0001_initial_identity
Create Date: 2026-11-26
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_relational_rbac"
down_revision: str | Sequence[str] | None = "0001_initial_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE_SCOPES = {
    "super_admin": "platform",
    "admin": "company",
    "user": "company",
}

PERMISSION_GRANTS = {
    "companies.read": ("super_admin",),
    "companies.create": ("super_admin",),
    "companies.update": ("super_admin",),
    "companies.deactivate": ("super_admin",),
    "companies.activate": ("super_admin",),
    "company.profile.read": ("admin",),
    "company.profile.update": ("admin",),
    "users.read_global": ("super_admin",),
    "users.create_global": ("super_admin",),
    "users.update_global": ("super_admin",),
    "users.deactivate_global": ("super_admin",),
    "users.activate_global": ("super_admin",),
    "users.reset_password_global": ("super_admin",),
    "users.revoke_sessions_global": ("super_admin",),
    "users.read_company": ("admin",),
    "users.create_company": ("admin",),
    "users.update_company": ("admin",),
    "users.deactivate_company": ("admin",),
    "users.activate_company": ("admin",),
    "users.reset_password_company": ("admin",),
    "users.revoke_sessions_company": ("admin",),
    "profile.read_own": ("super_admin", "admin", "user"),
    "profile.update_own": ("super_admin", "admin", "user"),
    "profile.change_password": ("super_admin", "admin", "user"),
    "audit.read_global": ("super_admin",),
    "audit.read_company": ("admin",),
}


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("scope IN ('platform', 'company')", name="ck_roles_scope"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_roles_code"),
        sa.UniqueConstraint("id", "scope", name="uq_roles_id_scope"),
    )
    op.create_table(
        "permissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("permission_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    role_ids = {
        code: uuid.uuid4()
        for code in ROLE_SCOPES
    }
    roles_table = sa.table(
        "roles",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("scope", sa.String()),
        sa.column("is_system", sa.Boolean()),
    )
    op.bulk_insert(
        roles_table,
        [
            {
                "id": role_ids["super_admin"],
                "code": "super_admin",
                "name": "Platform Super Admin",
                "scope": ROLE_SCOPES["super_admin"],
                "is_system": True,
            },
            {
                "id": role_ids["admin"],
                "code": "admin",
                "name": "Company Admin",
                "scope": ROLE_SCOPES["admin"],
                "is_system": True,
            },
            {
                "id": role_ids["user"],
                "code": "user",
                "name": "Company User",
                "scope": ROLE_SCOPES["user"],
                "is_system": True,
            },
        ],
    )

    permission_ids = {
        code: uuid.uuid4()
        for code in PERMISSION_GRANTS
    }
    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
    )
    op.bulk_insert(
        permissions_table,
        [
            {
                "id": permission_ids[code],
                "code": code,
                "description": code.replace(".", " ").replace("_", " ").title(),
            }
            for code in PERMISSION_GRANTS
        ],
    )
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )
    op.bulk_insert(
        role_permissions_table,
        [
            {"role_id": role_ids[role_code], "permission_id": permission_ids[permission_code]}
            for permission_code, role_codes in PERMISSION_GRANTS.items()
            for role_code in role_codes
        ],
    )

    op.add_column("users", sa.Column("role_id", sa.Uuid(), nullable=True))
    op.add_column("users", sa.Column("role_scope", sa.String(length=20), nullable=True))
    connection = op.get_bind()
    for role_code, role_scope in ROLE_SCOPES.items():
        connection.execute(
            sa.text(
                "UPDATE users SET role_id = :role_id, role_scope = :role_scope "
                "WHERE role = :role_code"
            ).bindparams(sa.bindparam("role_id", type_=sa.Uuid())),
            {
                "role_id": role_ids[role_code],
                "role_scope": role_scope,
                "role_code": role_code,
            },
        )

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("ck_users_role_company_id", type_="check")
        batch_op.create_check_constraint(
            "ck_users_role_scope_company_id",
            "(role_scope = 'platform' AND company_id IS NULL) OR "
            "(role_scope = 'company' AND company_id IS NOT NULL)",
        )
        batch_op.create_foreign_key(
            "fk_users_role_id_scope",
            "roles",
            ["role_id", "role_scope"],
            ["id", "scope"],
            ondelete="RESTRICT",
        )
        batch_op.alter_column("role_id", existing_type=sa.Uuid(), nullable=False)
        batch_op.alter_column("role_scope", existing_type=sa.String(length=20), nullable=False)
        batch_op.drop_column("role")

    op.create_index("ix_users_role_id", "users", ["role_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_role_id", table_name="users")
    op.add_column("users", sa.Column("role", sa.String(length=20), nullable=True))
    op.execute(
        sa.text(
            "UPDATE users SET role = "
            "(SELECT roles.code FROM roles WHERE roles.id = users.role_id)"
        )
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_role_id_scope", type_="foreignkey")
        batch_op.drop_constraint("ck_users_role_scope_company_id", type_="check")
        batch_op.drop_column("role_id")
        batch_op.drop_column("role_scope")
        batch_op.alter_column("role", existing_type=sa.String(length=20), nullable=False)
        batch_op.create_check_constraint(
            "ck_users_role_company_id",
            "(role = 'super_admin' AND company_id IS NULL) OR "
            "(role IN ('admin', 'user') AND company_id IS NOT NULL)",
        )

    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
