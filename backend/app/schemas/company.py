from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import CompanyStatus
from app.schemas.common import StrictSchema


class CompanyInitialAdmin(StrictSchema):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr


class CompanyCreateRequest(StrictSchema):
    legal_name: str = Field(min_length=1, max_length=200)
    display_name: str | None = Field(default=None, max_length=200)
    tax_id: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=2000)
    initial_admin: CompanyInitialAdmin


class CompanyUpdateRequest(StrictSchema):
    legal_name: str | None = Field(default=None, min_length=1, max_length=200)
    display_name: str | None = Field(default=None, max_length=200)
    tax_id: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=2000)


class CompanyStatusActionRequest(StrictSchema):
    reason: str | None = Field(default=None, max_length=500)
    confirmation: bool = Field(default=True)


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    legal_name: str
    display_name: str | None = None
    tax_id: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    status: CompanyStatus
    created_at: datetime
    updated_at: datetime
    deactivated_at: datetime | None = None
    users_count: int | None = None


class CompanyAdminCreatedResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: str
    status: str
    must_change_password: bool
    temporary_password: str | None = None


class CompanyCreateResponse(BaseModel):
    company: CompanyResponse
    initial_admin: CompanyAdminCreatedResponse
    delivery: dict[str, str]


class CompanyProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    legal_name: str
    display_name: str | None = None
    tax_id: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    status: CompanyStatus
    created_at: datetime
    updated_at: datetime


class CompanyProfileUpdateRequest(StrictSchema):
    display_name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=2000)
