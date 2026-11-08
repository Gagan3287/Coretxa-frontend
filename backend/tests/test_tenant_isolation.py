"""
THE proof-of-isolation test — see Section 4.1 of the build guide.

This doesn't just check that the app "forgets" to show Tenant B's data —
it proves the DATABASE ITSELF refuses to return it, even when:
  - queried with Tenant B's own session context, by exact document ID
  - the ID is known in advance (no guessing/enumeration required)
  - the query is a plain SELECT with no application-layer filtering at all

If this test ever fails, RLS is broken — full stop, nothing downstream
of the DB layer can be trusted until it's fixed.
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from app.core.database import tenant_session
from app.models import Bot, Document

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def bot_for_tenant_a(two_tenants):
    tenant_a_id, tenant_b_id, _, _ = two_tenants
    async with tenant_session(tenant_a_id) as session:
        bot = Bot(
            id=uuid.uuid4(),
            tenant_id=tenant_a_id,
            name="Isolation Bot",
            slug=f"iso-bot-{uuid.uuid4().hex[:6]}",
            widget_key_hash="hash",
            status="active",
        )
        session.add(bot)
        await session.flush()
        bot_id = bot.id
    return tenant_a_id, tenant_b_id, bot_id


async def test_tenant_b_cannot_read_tenant_a_document_by_id(bot_for_tenant_a):
    tenant_a_id, tenant_b_id, bot_id = bot_for_tenant_a

    # Tenant A creates a document.
    async with tenant_session(tenant_a_id) as session:
        doc = Document(
            id=uuid.uuid4(),
            tenant_id=tenant_a_id,
            bot_id=bot_id,
            original_filename="secret.pdf",
            status="ready",
        )
        session.add(doc)
        await session.flush()
        doc_id = doc.id

    # Sanity check: Tenant A can read its own document.
    async with tenant_session(tenant_a_id) as session:
        result = await session.execute(select(Document).where(Document.id == doc_id))
        assert result.scalar_one_or_none() is not None, "Tenant A should see its own document"

    # THE ACTUAL TEST: Tenant B, in its own correctly-scoped session,
    # queries for Tenant A's document BY ITS EXACT ID. This must return
    # nothing — RLS makes the row invisible.
    async with tenant_session(tenant_b_id) as session:
        result = await session.execute(select(Document).where(Document.id == doc_id))
        assert result.scalar_one_or_none() is None, (
            "CRITICAL: Tenant B was able to read Tenant A's document — RLS isolation is broken"
        )


async def test_no_tenant_context_sees_nothing(bot_for_tenant_a):
    """
    A session with app.tenant_id unset must see zero rows on tenant-scoped
    tables — the safe failure mode (fail closed, not fail open).
    """
    tenant_a_id, _, bot_id = bot_for_tenant_a
    async with tenant_session(tenant_a_id) as session:
        doc = Document(
            id=uuid.uuid4(),
            tenant_id=tenant_a_id,
            bot_id=bot_id,
            original_filename="x.pdf",
            status="ready",
        )
        session.add(doc)

    async with tenant_session(None) as session:
        result = await session.execute(select(Document))
        assert result.scalars().all() == [], "No tenant context should mean zero visible rows, not all rows"


async def test_direct_sql_cross_tenant_update_is_blocked(bot_for_tenant_a):
    """
    RLS applies to writes too, not just reads. Tenant B must not be able
    to UPDATE a row belonging to Tenant A even via a raw, hand-written
    UPDATE statement that specifies the exact primary key.
    """
    tenant_a_id, tenant_b_id, bot_id = bot_for_tenant_a

    async with tenant_session(tenant_a_id) as session:
        doc = Document(
            id=uuid.uuid4(),
            tenant_id=tenant_a_id,
            bot_id=bot_id,
            original_filename="orig.pdf",
            status="ready",
        )
        session.add(doc)
        await session.flush()
        doc_id = doc.id

    async with tenant_session(tenant_b_id) as session:
        await session.execute(
            text("UPDATE documents SET status = 'failed' WHERE id = :id"), {"id": str(doc_id)}
        )

    async with tenant_session(tenant_a_id) as session:
        result = await session.execute(select(Document).where(Document.id == doc_id))
        untouched = result.scalar_one()
        assert untouched.status == "ready", "Tenant B's UPDATE should not have affected Tenant A's row"
