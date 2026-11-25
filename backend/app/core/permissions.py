"""Permission constants and helpers.

The backend is the source of truth for authorization. Frontend checks are
only UX hints.
"""

PERMISSIONS: dict[str, set[str]] = {
    "companies.read": {"super_admin"},
    "companies.create": {"super_admin"},
    "companies.update": {"super_admin"},
    "companies.deactivate": {"super_admin"},
    "companies.activate": {"super_admin"},
    "company.profile.read": {"admin"},
    "company.profile.update": {"admin"},
    "users.read_global": {"super_admin"},
    "users.create_global": {"super_admin"},
    "users.update_global": {"super_admin"},
    "users.deactivate_global": {"super_admin"},
    "users.activate_global": {"super_admin"},
    "users.reset_password_global": {"super_admin"},
    "users.revoke_sessions_global": {"super_admin"},
    "users.read_company": {"admin"},
    "users.create_company": {"admin"},
    "users.update_company": {"admin"},
    "users.deactivate_company": {"admin"},
    "users.activate_company": {"admin"},
    "users.reset_password_company": {"admin"},
    "users.revoke_sessions_company": {"admin"},
    "profile.read_own": {"super_admin", "admin", "user"},
    "profile.update_own": {"super_admin", "admin", "user"},
    "profile.change_password": {"super_admin", "admin", "user"},
    "audit.read_global": {"super_admin"},
    "audit.read_company": {"admin"},
}


def roles_for_permission(permission: str) -> set[str]:
    """Return roles allowed for a permission, or an empty set if unknown."""
    return set(PERMISSIONS.get(permission, set()))


def permissions_for_role(role: str) -> list[str]:
    """Return sorted permissions granted to a role."""
    return sorted(
        permission for permission, roles in PERMISSIONS.items() if role in roles
    )
