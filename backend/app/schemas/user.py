from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole, UserStatus
from app.schemas.common import StrictSchema


class UserCompanySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    legal_name: str | None = None
    display_name: str | None = None
    status: str | None = None


class UserAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole
    status: UserStatus
    company_id: uuid.UUID | None = None
    company: UserCompanySummary | None = None
    must_change_password: bool = False
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    deactivated_at: datetime | None = None


class CompanyUserCreateRequest(StrictSchema):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    status: UserStatus = UserStatus.INVITED


class CompanyUserUpdateRequest(StrictSchema):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)


class GlobalUserCreateRequest(StrictSchema):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    role: UserRole
    company_id: uuid.UUID | None = None
    status: UserStatus = UserStatus.INVITED


class GlobalUserUpdateRequest(StrictSchema):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    role: UserRole | None = None
    status: UserStatus | None = None
    company_id: uuid.UUID | None = None
    must_change_password: bool | None = None


class UserActionRequest(StrictSchema):
    reason: str | None = Field(default=None, max_length=500)


class UserResetPasswordResponse(BaseModel):
    message: str
    reset_initiated: bool
    delivery: str
    temporary_password: str | None = None
    must_change_password: bool | None = None


class UserCreatedResponse(BaseModel):
    user: UserAdminResponse
    delivery: dict[str, str]
    temporary_password: str | None = None
