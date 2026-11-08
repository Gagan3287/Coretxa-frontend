"""
FastAPI dependencies chaining auth -> tenant context -> DB session.

Request flow for a normal (tenant-scoped) endpoint:
    Authorization: Bearer <jwt>
        -> get_current_claims()   decodes + validates the JWT
        -> get_tenant_db()        opens a session, SET LOCAL app.tenant_id
                                  from the JWT's tenant_id claim
    Every query inside that endpoint is now automatically RLS-scoped.

For platform-admin-only endpoints (tenant provisioning), use
get_current_platform_admin() + platform_session() instead -- see
app/api/tenants.py.

For widget-facing endpoints (Phase 3 /query), use get_bot_context() --
it reads X-Widget-Key, looks the bot up by hashed key via the
resolve_widget_key() SECURITY DEFINER function (see migration 0005), and
returns a WidgetContext with both tenant_id and bot_id so the handler can
open a properly scoped tenant_session.
"""
from dataclasses import dataclass
from typing import AsyncIterator
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import platform_session, tenant_session
from app.core.security import decode_token, hash_widget_key

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_claims(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = decode_token(creds.credentials)
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not an access token")
    return payload


async def get_tenant_db(
    claims: dict = Depends(get_current_claims),
) -> AsyncIterator[AsyncSession]:
    if claims.get("platform_admin"):
        # Platform admins have no tenant_id — they shouldn't hit tenant-scoped routes.
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Platform admins cannot access tenant routes")
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token missing tenant_id")
    async with tenant_session(UUID(tenant_id)) as session:
        yield session


def require_role(*allowed_roles: str):
    """Route dependency factory: require_role("tenant_admin") etc."""

    def _check(claims: dict = Depends(get_current_claims)) -> dict:
        if claims.get("role") not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role for this action")
        return claims

    return _check


def get_current_platform_admin(claims: dict = Depends(get_current_claims)) -> dict:
    if not claims.get("platform_admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Platform admin access required")
    return claims


# ---------------------------------------------------------------------------
# Widget auth — used ONLY by Phase-3 /query endpoint, NOT by admin routes
# ---------------------------------------------------------------------------


@dataclass
class WidgetContext:
    """Resolved bot + tenant context for widget-key-authenticated requests."""

    bot_id: UUID
    tenant_id: UUID
    bot_status: str


async def get_bot_context(
    x_widget_key: str = Header(..., alias="X-Widget-Key"),
) -> WidgetContext:
    """
    Authenticate a request via the X-Widget-Key header.

    Lookup strategy:
      1. Fail fast on obviously wrong format (no DB hit).
      2. SHA-256 hash the incoming key.
      3. Call resolve_widget_key(:hash) -- a SECURITY DEFINER SQL function
         (created by migration 0005) that runs as postgres (bypassing RLS)
         and returns only bot_id, tenant_id, status.

         Why a function instead of a direct SELECT on bots:
         platform_session() does SET LOCAL ROLE cortexa_app before any
         query.  bots has FORCE ROW LEVEL SECURITY, and with no
         app.tenant_id set, cortexa_app sees zero rows -- every widget
         request would 401.  The SECURITY DEFINER function resolves this
         without granting cortexa_app BYPASSRLS or superuser.

      4. If found and active, return a WidgetContext.
      5. If not found or inactive: 401 with a generic message.

    Only bot_id, tenant_id, and status are returned -- widget_key_hash,
    llm_overrides, and other sensitive fields are NOT exposed.
    """
    if not x_widget_key.startswith("wgt_"):
        # Fail fast on obviously wrong format without hitting the DB.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid widget key")

    key_hash = hash_widget_key(x_widget_key)

    async with platform_session() as session:
        result = await session.execute(
            text("SELECT bot_id, tenant_id, status FROM public.resolve_widget_key(:hash)"),
            {"hash": key_hash},
        )
        row = result.one_or_none()

    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid widget key")

    bot_id, tenant_id, bot_status = row
    if bot_status != "active":
        # Don't reveal the key is valid -- treat inactive the same as missing.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid widget key")

    return WidgetContext(
        bot_id=UUID(str(bot_id)),
        tenant_id=UUID(str(tenant_id)),
        bot_status=bot_status,
    )
