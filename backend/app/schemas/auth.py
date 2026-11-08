from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class TenantLoginRequest(BaseModel):
    tenant_slug: str
    email: EmailStr
    password: str


class PlatformLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TenantRegisterRequest(BaseModel):
    full_name: str | None = None
    org_name: str = Field(..., min_length=2, max_length=100)
    org_slug: str = Field(..., pattern=r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$")
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")
    password: str = Field(..., min_length=8)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserMeResponse(BaseModel):
    id: UUID
    full_name: str | None = None
    email: str
    tenant_slug: str | None = None
    tenant_id: UUID | None = None
    role: str

