from __future__ import annotations

import uuid

from fastapi import Depends

from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.services.tenant_service import company_id_for_user


async def get_authenticated_company_id(
    current_user: User = Depends(get_current_user),
) -> uuid.UUID:
    return company_id_for_user(current_user)
