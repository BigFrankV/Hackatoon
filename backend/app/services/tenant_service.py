from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import CHAR, Select
from sqlalchemy.sql.dml import Update

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.user import User


def company_id_for_user(user: User) -> uuid.UUID:
    if user.company_id is None:
        raise PermissionDeniedError(
            "Company context required", code="company_context_required"
        )
    return user.company_id


def assert_company_access(user: User, resource_company_id: uuid.UUID) -> uuid.UUID:
    authenticated_company_id = company_id_for_user(user)
    if authenticated_company_id != resource_company_id:
        raise NotFoundError()
    return authenticated_company_id


def scope_statement_to_company(
    statement: Select[Any] | Update,
    entity: Any,
    company_id: uuid.UUID,
) -> Select[Any] | Update:
    columns = getattr(entity, "c", None)
    company_column = (
        columns.get("company_id")
        if columns is not None
        else getattr(entity, "company_id", None)
    )
    if company_column is None:
        raise TypeError(f"{entity!r} is not company-scoped")
    value = str(company_id) if isinstance(company_column.type, CHAR) else company_id
    return statement.where(company_column == value)
