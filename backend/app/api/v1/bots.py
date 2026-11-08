"""
Bot management — tenant_admin only.

POST  /api/v1/bots          — create a new bot (enforces tenant.max_bots limit)
GET   /api/v1/bots          — list all bots for the caller's tenant
GET   /api/v1/bots/{bot_id} — single bot detail

Widget-key auth (get_bot_context) is in app/deps.py and will be wired to
the /query endpoint in Phase 3 — it is NOT used here.
"""
import secrets
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import tenant_session
from app.core.security import hash_widget_key
from app.deps import get_current_claims, require_role
from app.models import AuditLog, Bot, Document, Tenant
from app.schemas.bot import (
    BotCreateRequest,
    BotCreateResponse,
    BotDetail,
    BotListResponse,
    BotUpdateRequest,
)

router = APIRouter(prefix="/bots", tags=["bots"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bot_to_detail(bot: Bot, document_count: int = 0) -> BotDetail:
    return BotDetail(
        bot_id=bot.id,
        tenant_id=bot.tenant_id,
        name=bot.name,
        slug=bot.slug,
        branding_json=bot.branding_json,
        status=bot.status,
        document_count=document_count,
        created_at=bot.created_at,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/bots — create bot
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=BotCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new bot for the caller's tenant",
)
async def create_bot(
    body: BotCreateRequest,
    claims: dict = Depends(require_role("tenant_admin")),
) -> BotCreateResponse:
    tenant_id = UUID(claims["tenant_id"])

    async with tenant_session(tenant_id) as session:
        # 1. Load tenant to check max_bots limit
        tenant_result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = tenant_result.scalar_one_or_none()
        if tenant is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")

        # 2. Count existing bots for this tenant (RLS scopes this automatically)
        count_result = await session.execute(select(func.count()).select_from(Bot))
        current_count: int = count_result.scalar_one()

        if current_count >= tenant.max_bots:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "bot_limit_reached",
                    "message": (
                        f"Your current plan allows {tenant.max_bots} bot(s). "
                        "Upgrade your plan to create more."
                    ),
                    "current_count": current_count,
                    "limit": tenant.max_bots,
                },
            )

        # 3. Check slug uniqueness within tenant (composite unique enforced at DB too)
        slug_exists = await session.execute(select(Bot).where(Bot.slug == body.slug))
        if slug_exists.scalar_one_or_none() is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"A bot with slug '{body.slug}' already exists for this tenant.",
            )

        # 4. Generate widget key — returned raw ONCE, only hash stored
        raw_widget_key = f"wgt_{secrets.token_urlsafe(32)}"
        widget_key_hash = hash_widget_key(raw_widget_key)

        bot = Bot(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=body.name,
            slug=body.slug,
            widget_key_hash=widget_key_hash,
            branding_json=body.branding_json,
            llm_overrides=body.llm_overrides,
            status="active",
        )
        session.add(bot)
        await session.flush()  # get bot.id before audit log

        # 5. Write audit log
        audit = AuditLog(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            actor_id=UUID(claims["sub"]),
            action="bot.created",
            details={"bot_id": str(bot.id), "slug": bot.slug, "name": bot.name},
        )
        session.add(audit)

    return BotCreateResponse(
        bot_id=bot.id,
        slug=bot.slug,
        name=bot.name,
        status=bot.status,
        widget_key=raw_widget_key,
        created_at=bot.created_at,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/bots — list bots
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=BotListResponse,
    summary="List all bots for the caller's tenant",
)
async def list_bots(
    claims: dict = Depends(require_role("tenant_admin")),
) -> BotListResponse:
    tenant_id = UUID(claims["tenant_id"])

    async with tenant_session(tenant_id) as session:
        result = await session.execute(select(Bot).order_by(Bot.created_at))
        bots = result.scalars().all()

        # Query document counts grouped by bot_id for this tenant (single query, no N+1)
        doc_count_result = await session.execute(
            select(Document.bot_id, func.count(Document.id)).group_by(Document.bot_id)
        )
        doc_counts = dict(doc_count_result.all())

    return BotListResponse(
        bots=[_bot_to_detail(b, doc_counts.get(b.id, 0)) for b in bots],
        total=len(bots),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/bots/{bot_id} — single bot detail
# ---------------------------------------------------------------------------


@router.get(
    "/{bot_id}",
    response_model=BotDetail,
    summary="Get details of a specific bot",
)
async def get_bot(
    bot_id: UUID,
    claims: dict = Depends(require_role("tenant_admin")),
) -> BotDetail:
    tenant_id = UUID(claims["tenant_id"])

    async with tenant_session(tenant_id) as session:
        result = await session.execute(select(Bot).where(Bot.id == bot_id))
        bot = result.scalar_one_or_none()

        if bot is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Bot not found")

        doc_count_result = await session.execute(
            select(func.count(Document.id)).where(Document.bot_id == bot_id)
        )
        doc_count = doc_count_result.scalar_one()

    return _bot_to_detail(bot, doc_count)


# ---------------------------------------------------------------------------
# PATCH /api/v1/bots/{bot_id} — update bot name and branding_json
# ---------------------------------------------------------------------------


@router.patch(
    "/{bot_id}",
    response_model=BotDetail,
    summary="Update bot name and branding_json (merges branding_json)",
)
async def update_bot(
    bot_id: UUID,
    body: BotUpdateRequest,
    claims: dict = Depends(require_role("tenant_admin")),
) -> BotDetail:
    """
    Update a bot's name and/or branding configuration.

    Branding JSON behavior:
    - Merges provided top-level keys into existing branding_json.
    - Preserves existing keys not included in the payload.
    - Tenant-isolated via RLS.
    """
    tenant_id = UUID(claims["tenant_id"])

    async with tenant_session(tenant_id) as session:
        result = await session.execute(select(Bot).where(Bot.id == bot_id))
        bot = result.scalar_one_or_none()

        if bot is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Bot not found")

        updated_fields: dict[str, str] = {}

        if body.name is not None:
            bot.name = body.name
            updated_fields["name"] = body.name

        if body.branding_json is not None:
            current_branding = dict(bot.branding_json or {})
            current_branding.update(body.branding_json)
            bot.branding_json = current_branding
            flag_modified(bot, "branding_json")
            updated_fields["branding_json"] = "updated"

        if updated_fields:
            audit = AuditLog(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                actor_id=UUID(claims["sub"]),
                action="bot.updated",
                details={"bot_id": str(bot_id), "updated_fields": list(updated_fields.keys())},
            )
            session.add(audit)

        doc_count_result = await session.execute(
            select(func.count(Document.id)).where(Document.bot_id == bot_id)
        )
        doc_count = doc_count_result.scalar_one()

    return _bot_to_detail(bot, doc_count)

