"""
Tenant and initial tenant-admin user provisioning service.

Shared between:
- POST /tenants (platform-admin provisioned)
- POST /auth/register (public self-service registration)
"""
from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select

from app.core.database import platform_session, tenant_session
from app.core.security import hash_password
from app.models import Tenant, User


@dataclass
class ProvisioningResult:
    tenant_id: uuid.UUID
    tenant_slug: str
    tenant_name: str
    user_id: uuid.UUID
    user_email: str
    raw_api_key: str


async def provision_tenant_and_admin(
    name: str,
    slug: str,
    admin_email: str,
    admin_password: str,
    full_name: str | None = None,
    phone: str | None = None,
) -> ProvisioningResult:
    """
    Core provisioning logic:
    1. Validates slug uniqueness.
    2. Creates the Tenant record in a platform session.
    3. Creates the initial User (role='tenant_admin') in a tenant session.
    """
    clean_slug = slug.lower().strip()
    api_key = f"ctx_{secrets.token_urlsafe(32)}"
    tenant_id = uuid.uuid4()

    # 1. Platform session to create Tenant
    async with platform_session() as session:
        existing = await session.execute(select(Tenant).where(Tenant.slug == clean_slug))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="That organization address is already taken.",
            )

        tenant = Tenant(
            id=tenant_id,
            name=name.strip(),
            slug=clean_slug,
            api_key_hash=hash_password(api_key),
        )
        session.add(tenant)

    # 2. Tenant session to create tenant_admin user
    user_id = uuid.uuid4()
    async with tenant_session(tenant_id) as session:
        user_check = await session.execute(select(User).where(User.email == admin_email.strip()))
        if user_check.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with that email already exists for this organization.",
            )

        admin_user = User(
            id=user_id,
            tenant_id=tenant_id,
            email=admin_email.strip(),
            password_hash=hash_password(admin_password),
            role="tenant_admin",
            full_name=full_name.strip() if full_name else None,
            phone=phone.strip() if phone else None,
        )
        session.add(admin_user)

    return ProvisioningResult(
        tenant_id=tenant_id,
        tenant_slug=clean_slug,
        tenant_name=name.strip(),
        user_id=user_id,
        user_email=admin_email.strip(),
        raw_api_key=api_key,
    )
