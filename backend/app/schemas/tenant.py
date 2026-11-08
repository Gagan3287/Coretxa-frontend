from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class TenantProvisionRequest(BaseModel):
    name: str
    slug: str = Field(pattern=r"^[a-z0-9-]{3,63}$")
    admin_email: EmailStr
    admin_password: str = Field(min_length=8)


class TenantProvisionResponse(BaseModel):
    tenant_id: UUID
    slug: str
    api_key: str  # returned ONCE at creation — only the hash is stored
