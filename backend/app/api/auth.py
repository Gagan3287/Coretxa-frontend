"""
Two separate login flows, deliberately kept apart:

  POST /auth/login           tenant_slug + email + password -> tenant-scoped user
  POST /auth/platform-login  email + password -> platform admin (no tenant)
  POST /auth/register        public self-service onboarding
  GET  /auth/me              authenticated user details
  POST /auth/refresh         refresh access token
"""
import secrets
import time
import uuid
from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy import select

from app.core.database import platform_session, tenant_session
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.deps import get_current_claims
from app.models import PlatformAdmin, Tenant, User
from app.schemas.auth import (
    PlatformLoginRequest,
    RefreshTokenRequest,
    TenantLoginRequest,
    TenantRegisterRequest,
    TokenResponse,
    UserMeResponse,
)

from app.services.provisioning import provision_tenant_and_admin

router = APIRouter(prefix="/auth", tags=["auth"])

RESERVED_SLUGS = {
    "admin",
    "api",
    "www",
    "app",
    "platform",
    "cortexa",
    "system",
    "auth",
    "support",
    "billing",
    "root",
    "internal",
    "dashboard",
    "mail",
    "help",
    "static",
    "assets",
    "public",
}

# In-memory sliding window rate limiter: IP -> timestamps
_REGISTRATION_WINDOW_SECONDS = 60
_REGISTRATION_MAX_REQUESTS = 10
_registration_attempts: dict[str, list[float]] = defaultdict(list)


def _check_registration_rate_limit(client_ip: str) -> None:
    now = time.time()
    cutoff = now - _REGISTRATION_WINDOW_SECONDS
    timestamps = [t for t in _registration_attempts[client_ip] if t > cutoff]
    if len(timestamps) >= _REGISTRATION_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Registration rate limit exceeded. Please wait a minute and try again.",
        )
    timestamps.append(now)
    _registration_attempts[client_ip] = timestamps


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: TenantRegisterRequest, request: Request) -> TokenResponse:
    # 1. Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    _check_registration_rate_limit(client_ip)

    # 2. Reserved slug check
    slug = body.org_slug.lower().strip()
    if slug in RESERVED_SLUGS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That organization address is reserved. Please choose another.",
        )

    # 3. Call shared provisioning logic
    result = await provision_tenant_and_admin(
        name=body.org_name,
        slug=slug,
        admin_email=body.email,
        admin_password=body.password,
        full_name=body.full_name,
        phone=body.phone,
    )

    return TokenResponse(
        access_token=create_access_token(
            user_id=result.user_id,
            tenant_id=result.tenant_id,
            role="tenant_admin",
        ),
        refresh_token=create_refresh_token(user_id=result.user_id, tenant_id=result.tenant_id),
    )


@router.post("/login", response_model=TokenResponse)
async def tenant_login(body: TenantLoginRequest) -> TokenResponse:
    async with platform_session() as session:
        result = await session.execute(select(Tenant).where(Tenant.slug == body.tenant_slug))
        tenant = result.scalar_one_or_none()

    if tenant is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    async with tenant_session(tenant.id) as session:
        result = await session.execute(select(User).where(User.email == body.email))
        user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    return TokenResponse(
        access_token=create_access_token(user_id=user.id, tenant_id=tenant.id, role=user.role),
        refresh_token=create_refresh_token(user_id=user.id, tenant_id=tenant.id),
    )


@router.post("/platform-login", response_model=TokenResponse)
async def platform_login(body: PlatformLoginRequest) -> TokenResponse:
    async with platform_session() as session:
        result = await session.execute(
            select(PlatformAdmin).where(PlatformAdmin.email == body.email)
        )
        admin = result.scalar_one_or_none()

    if admin is None or not verify_password(body.password, admin.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    return TokenResponse(
        access_token=create_access_token(
            user_id=admin.id, tenant_id=None, role="platform_admin", is_platform_admin=True
        ),
        refresh_token=create_refresh_token(user_id=admin.id, tenant_id=None),
    )


@router.get("/me", response_model=UserMeResponse)
async def get_me(claims: dict = Depends(get_current_claims)) -> UserMeResponse:
    user_id = UUID(claims["sub"])
    is_platform = claims.get("platform_admin", False)

    if is_platform:
        async with platform_session() as session:
            result = await session.execute(
                select(PlatformAdmin).where(PlatformAdmin.id == user_id)
            )
            admin = result.scalar_one_or_none()
            if admin is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
            return UserMeResponse(
                id=user_id,
                full_name="Platform Admin",
                email=admin.email,
                tenant_slug=None,
                tenant_id=None,
                role="platform_admin",
            )

    tenant_id_str = claims.get("tenant_id")
    if not tenant_id_str:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token claims")

    tenant_id = UUID(tenant_id_str)
    async with tenant_session(tenant_id) as session:
        u_res = await session.execute(select(User).where(User.id == user_id))
        user = u_res.scalar_one_or_none()
        if user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

        t_res = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = t_res.scalar_one_or_none()
        tenant_slug = tenant.slug if tenant else None

    return UserMeResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        tenant_slug=tenant_slug,
        tenant_id=tenant_id,
        role=user.role,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshTokenRequest) -> TokenResponse:
    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token type")

    user_id = UUID(payload["sub"])
    tenant_id_str = payload.get("tenant_id")
    tenant_id = UUID(tenant_id_str) if tenant_id_str else None

    if tenant_id is None:
        # Platform admin refresh
        async with platform_session() as session:
            admin_res = await session.execute(
                select(PlatformAdmin).where(PlatformAdmin.id == user_id)
            )
            if admin_res.scalar_one_or_none() is None:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
        role = "platform_admin"
        is_platform = True
    else:
        async with tenant_session(tenant_id) as session:
            user_res = await session.execute(select(User).where(User.id == user_id))
            user = user_res.scalar_one_or_none()
            if user is None:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
            role = user.role
            is_platform = False

    return TokenResponse(
        access_token=create_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
            is_platform_admin=is_platform,
        ),
        refresh_token=create_refresh_token(user_id=user_id, tenant_id=tenant_id),
    )

