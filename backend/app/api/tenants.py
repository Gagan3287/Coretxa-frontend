"""
Tenant provisioning — platform-admin only. This is the ONE place a new
tenant_id gets minted; everything downstream (users, documents, chunks)
depends on this row existing first.
"""
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.core.database import platform_session, tenant_session
from app.core.security import hash_password
from app.deps import get_current_platform_admin
from app.schemas.tenant import TenantProvisionRequest, TenantProvisionResponse
from app.services.provisioning import provision_tenant_and_admin

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantProvisionResponse, status_code=status.HTTP_201_CREATED)
async def provision_tenant(
    body: TenantProvisionRequest,
    _admin: dict = Depends(get_current_platform_admin),
) -> TenantProvisionResponse:
    result = await provision_tenant_and_admin(
        name=body.name,
        slug=body.slug,
        admin_email=body.admin_email,
        admin_password=body.admin_password,
    )

    return TenantProvisionResponse(
        tenant_id=result.tenant_id,
        slug=result.tenant_slug,
        api_key=result.raw_api_key,
    )
