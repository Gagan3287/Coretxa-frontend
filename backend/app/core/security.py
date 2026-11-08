"""
Password hashing and JWT issuing/verification.

Note on widget key hashing
--------------------------
Widget keys are 256-bit random tokens (secrets.token_urlsafe(32)).  A random
token of that entropy does not need bcrypt's work-factor to resist brute-force:
there is no brute-forceable space.  What it needs is a fast, indexed equality
lookup in the database.  SHA-256 (stored as 64 hex chars) gives us that:

  - O(1) lookup via UNIQUE index (no table scan, no per-row compare loop)
  - Constant-time hex comparison is safe because SHA-256 is not a secret;
    the security comes from the raw key's entropy
  - No bcrypt round-trip overhead on every widget request
"""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_widget_key(raw_key: str) -> str:
    """Return the SHA-256 hex digest of a raw widget key.

    Used to store and look up widget keys without bcrypt overhead.  Only
    call this with a key that already has the 'wgt_' prefix — the prefix
    is part of the value being hashed.
    """
    return hashlib.sha256(raw_key.encode()).hexdigest()


def create_access_token(
    *, user_id: UUID, tenant_id: UUID | None, role: str, is_platform_admin: bool = False
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "platform_admin": is_platform_admin,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    if tenant_id is not None:
        payload["tenant_id"] = str(tenant_id)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(*, user_id: UUID, tenant_id: UUID | None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh",
    }
    if tenant_id is not None:
        payload["tenant_id"] = str(tenant_id)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Raises jose.JWTError on invalid/expired tokens — callers turn that into a 401."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
