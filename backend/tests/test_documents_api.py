import uuid
from uuid import UUID
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import tenant_session
from app.core.security import create_access_token
from app.main import app
from app.models import Bot, Chunk, Document, DocumentVersion, Tenant
from app.worker.ingestion import process_one
from app.worker.queue import DLQ_KEY, get_redis

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixture for a test bot
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_bot(two_tenants):
    tenant_a_id, tenant_b_id, user_a_id, user_b_id = two_tenants
    async with tenant_session(tenant_a_id) as session:
        bot = Bot(
            id=uuid.uuid4(),
            tenant_id=tenant_a_id,
            name="Test Bot A",
            slug=f"test-bot-{uuid.uuid4().hex[:6]}",
            widget_key_hash=f"hash_{uuid.uuid4().hex[:8]}",
            status="active",
        )
        session.add(bot)
        await session.flush()
        bot_id = bot.id

    return tenant_a_id, tenant_b_id, user_a_id, user_b_id, bot_id


def _make_pdf(text: str) -> bytes:
    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(100, 700, text)
    c.showPage()
    c.save()
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 3a. Forced 3x ingestion failure -> DLQ write + failed status on ver & doc
# ---------------------------------------------------------------------------


async def test_3a_forced_ingestion_failure_dlq(test_bot):
    tenant_a_id, _, _, _, bot_id = test_bot
    r = get_redis()
    await r.flushdb()

    # Create document & version
    async with tenant_session(tenant_a_id) as session:
        doc = Document(
            id=uuid.uuid4(),
            tenant_id=tenant_a_id,
            bot_id=bot_id,
            original_filename="fail_test.txt",
            status="pending",
        )
        session.add(doc)
        await session.flush()

        ver = DocumentVersion(
            id=uuid.uuid4(),
            tenant_id=tenant_a_id,
            bot_id=bot_id,
            document_id=doc.id,
            version_number=1,
            file_path="non_existent_file.txt",
            status="pending",
        )
        session.add(ver)
        await session.flush()
        doc_id, ver_id = doc.id, ver.id

    # Attempt 1 -> fails -> sleeps -> re-queues attempt 2
    msg_id_1 = "1000-0"
    fields_1 = {
        "document_version_id": str(ver_id),
        "tenant_id": str(tenant_a_id),
        "bot_id": str(bot_id),
        "attempt": "1",
    }
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await process_one(r, msg_id_1, fields_1)

    # Attempt 2 -> fails -> sleeps -> re-queues attempt 3
    fields_2 = {**fields_1, "attempt": "2"}
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await process_one(r, "2000-0", fields_2)

    # Attempt 3 (MAX_ATTEMPTS) -> terminal failure
    fields_3 = {**fields_1, "attempt": "3"}
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await process_one(r, "3000-0", fields_3)

    # Verify DLQ message in Redis
    dlq_messages = await r.xrange(DLQ_KEY)
    assert len(dlq_messages) == 1
    dlq_id, dlq_fields = dlq_messages[0]
    assert dlq_fields["document_version_id"] == str(ver_id)
    assert "FileNotFoundError" in dlq_fields["error"]

    # Verify DB state: DocumentVersion AND Document both failed with SAME error
    async with tenant_session(tenant_a_id) as session:
        v_res = await session.execute(select(DocumentVersion).where(DocumentVersion.id == ver_id))
        ver_row = v_res.scalar_one()
        assert ver_row.status == "failed"
        assert ver_row.error_message is not None

        d_res = await session.execute(select(Document).where(Document.id == doc_id))
        doc_row = d_res.scalar_one()
        assert doc_row.status == "failed"
        assert doc_row.error_message == ver_row.error_message


# ---------------------------------------------------------------------------
# 3b. Upload v2 while v1 is ready -> v1 chunks served until v2 worker finishes
# ---------------------------------------------------------------------------


async def test_3b_v1_served_while_v2_pending(test_bot, tmp_path):
    tenant_a_id, _, user_a_id, _, bot_id = test_bot

    token = create_access_token(
        user_id=user_a_id, tenant_id=tenant_a_id, role="tenant_admin"
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Setup v1 as ready
    file_v1 = tmp_path / "v1.txt"
    file_v1.write_text("Version 1 content")

    async with tenant_session(tenant_a_id) as session:
        doc = Document(
            id=uuid.uuid4(),
            tenant_id=tenant_a_id,
            bot_id=bot_id,
            original_filename="doc.txt",
            status="ready",
        )
        session.add(doc)
        await session.flush()

        ver1 = DocumentVersion(
            id=uuid.uuid4(),
            tenant_id=tenant_a_id,
            bot_id=bot_id,
            document_id=doc.id,
            version_number=1,
            file_path=str(file_v1),
            status="ready",
        )
        session.add(ver1)
        await session.flush()
        doc.current_version_id = ver1.id

        chunk1 = Chunk(
            id=uuid.uuid4(),
            tenant_id=tenant_a_id,
            bot_id=bot_id,
            document_id=doc.id,
            document_version_id=ver1.id,
            content="V1 Chunk Text",
            chunk_index=0,
            token_count=3,
            embedding=[0.1] * 768,
        )
        session.add(chunk1)
        doc_id, v1_id = doc.id, ver1.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Verify GET /documents/{id}/chunks serves V1 chunk before uploading V2
        c_res1 = await client.get(f"/api/v1/bots/{bot_id}/documents/{doc_id}/chunks", headers=headers)
        assert c_res1.status_code == 200
        assert c_res1.json()["chunks"][0]["content"] == "V1 Chunk Text"

        # 2. Upload V2 (creates V2 in pending state)
        pdf_v2 = _make_pdf("Version 2 content has been successfully updated.")
        with patch("app.api.v1.documents.enqueue", new_callable=AsyncMock):
            v2_res = await client.post(
                f"/api/v1/bots/{bot_id}/documents",
                headers=headers,
                data={"document_id": str(doc_id)},
                files={"file": ("v2.pdf", pdf_v2, "application/pdf")},
            )
            assert v2_res.status_code == 201
            v2_id = v2_res.json()["version_id"]

        # 3. GET chunks WITHOUT version_id specified -> STILL SERVES V1 chunks!
        c_res2 = await client.get(f"/api/v1/bots/{bot_id}/documents/{doc_id}/chunks", headers=headers)
        assert c_res2.status_code == 200
        data2 = c_res2.json()
        assert data2["total"] == 1
        assert data2["chunks"][0]["content"] == "V1 Chunk Text"

        # 4. Now process V2 through worker
        r = get_redis()
        with patch("app.worker.ingestion._embed_chunks", new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [[0.2] * 768]
            fields_v2 = {
                "document_version_id": str(v2_id),
                "tenant_id": str(tenant_a_id),
                "bot_id": str(bot_id),
                "attempt": "1",
            }
            await process_one(r, "v2-msg-1", fields_v2)

        # 5. After V2 worker finishes -> GET chunks WITHOUT version_id NOW SERVES V2 chunks!
        c_res3 = await client.get(f"/api/v1/bots/{bot_id}/documents/{doc_id}/chunks", headers=headers)
        assert c_res3.status_code == 200
        data3 = c_res3.json()
        assert "Version 2 content" in data3["chunks"][0]["content"]
        assert data3["chunks"][0]["document_version_id"] == str(v2_id)


# ---------------------------------------------------------------------------
# 3c. Chunk tenant isolation (exact chunk ID query by Tenant B returns nothing)
# ---------------------------------------------------------------------------


async def test_3c_chunk_tenant_isolation(test_bot):
    tenant_a_id, tenant_b_id, _, _, bot_id = test_bot
    chunk_id = uuid.uuid4()

    # Tenant A creates a document version and a chunk
    async with tenant_session(tenant_a_id) as session:
        doc = Document(id=uuid.uuid4(), tenant_id=tenant_a_id, bot_id=bot_id, original_filename="a.txt", status="ready")
        session.add(doc)
        await session.flush()

        ver = DocumentVersion(id=uuid.uuid4(), tenant_id=tenant_a_id, bot_id=bot_id, document_id=doc.id, version_number=1, file_path="a.txt", status="ready")
        session.add(ver)
        await session.flush()

        chunk = Chunk(
            id=chunk_id,
            tenant_id=tenant_a_id,
            bot_id=bot_id,
            document_id=doc.id,
            document_version_id=ver.id,
            content="Secret Tenant A Chunk Content",
            chunk_index=0,
            embedding=[0.1] * 768,
        )
        session.add(chunk)

    # Sanity check: Tenant A sees its chunk
    async with tenant_session(tenant_a_id) as session:
        res = await session.execute(select(Chunk).where(Chunk.id == chunk_id))
        assert res.scalar_one_or_none() is not None

    # THE TEST: Tenant B in its own session queries by exact chunk_id -> MUST return None via RLS
    async with tenant_session(tenant_b_id) as session:
        res_b = await session.execute(select(Chunk).where(Chunk.id == chunk_id))
        assert res_b.scalar_one_or_none() is None, "CRITICAL: Tenant B was able to read Tenant A's chunk row!"


# ---------------------------------------------------------------------------
# 3d. File named handbook.pdf with JPEG bytes -> 400 Bad Request
# ---------------------------------------------------------------------------


async def test_3d_pdf_extension_with_jpeg_bytes_rejected(test_bot):
    tenant_a_id, _, user_a_id, _, bot_id = test_bot

    token = create_access_token(
        user_id=user_a_id, tenant_id=tenant_a_id, role="tenant_admin"
    )
    headers = {"Authorization": f"Bearer {token}"}

    # JPEG header bytes: \xFF\xD8\xFF\xE0
    jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00\x48\x00\x48\x00\x00"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/bots/{bot_id}/documents",
            headers=headers,
            files={"file": ("handbook.pdf", jpeg_bytes, "application/pdf")},
        )

    assert response.status_code == 400, response.text
    err = response.json()["detail"]
    assert err["error"] == "invalid_file_format"

    # Verify no Document row was written
    async with tenant_session(tenant_a_id) as session:
        res = await session.execute(select(Document).where(Document.original_filename == "handbook.pdf"))
        assert res.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# 3e. Tenant at storage_quota_mb ceiling -> 413 Request Entity Too Large
# ---------------------------------------------------------------------------


async def test_3e_storage_quota_exceeded_rejected(test_bot):
    tenant_a_id, _, user_a_id, _, bot_id = test_bot

    # Set Tenant A storage_quota_mb = 1 MB (1,048,576 bytes)
    async with tenant_session(tenant_a_id) as session:
        t_res = await session.execute(select(Tenant).where(Tenant.id == tenant_a_id))
        tenant = t_res.scalar_one()
        tenant.storage_quota_mb = 1

    token = create_access_token(
        user_id=user_a_id, tenant_id=tenant_a_id, role="tenant_admin"
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to upload 2 MB file (2 * 1024 * 1024 bytes)
    base_pdf = _make_pdf("Small PDF content for quota testing.")
    big_file_bytes = base_pdf + b"\n% " + b"X" * (2 * 1024 * 1024)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/bots/{bot_id}/documents",
            headers=headers,
            files={"file": ("large_file.pdf", big_file_bytes, "application/pdf")},
        )

    assert response.status_code == 413, response.text
    err = response.json()["detail"]
    assert err["error"] == "storage_quota_exceeded"
    assert err["quota_mb"] == 1

    # Verify no Document row was written
    async with tenant_session(tenant_a_id) as session:
        res = await session.execute(select(Document).where(Document.original_filename == "large_file.txt"))
        assert res.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# 3f. First-ever upload: full path upload -> pending -> worker -> ready
# ---------------------------------------------------------------------------


async def test_3f_initial_upload_creates_document_and_v1(test_bot, tmp_path):
    """
    POST a brand-new document (no prior Document row for this bot) through
    the real API.  Assert the DB is in 'pending' immediately after the upload,
    then run process_one() (embeddings mocked) and assert Document flips to
    'ready', current_version_id is set, and GET .../chunks serves the chunks.
    """
    tenant_a_id, _, user_a_id, _, bot_id = test_bot

    token = create_access_token(
        user_id=user_a_id, tenant_id=tenant_a_id, role="tenant_admin"
    )
    headers = {"Authorization": f"Bearer {token}"}

    file_content = _make_pdf("This is the first version of a brand new document.")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Upload new document — no document_id supplied, so API must create one
        with patch("app.api.v1.documents.enqueue", new_callable=AsyncMock):
            upload_res = await client.post(
                f"/api/v1/bots/{bot_id}/documents",
                headers=headers,
                files={"file": ("first_upload.pdf", file_content, "application/pdf")},
            )
        assert upload_res.status_code == 201, upload_res.text
        body = upload_res.json()

        doc_id = body["document_id"]
        ver_id = body["version_id"]
        assert body["version_number"] == 1
        assert body["status"] == "pending"

        # 2. Assert DB state immediately after upload: pending, current_version_id is NULL
        async with tenant_session(tenant_a_id) as session:
            d_res = await session.execute(select(Document).where(Document.id == UUID(doc_id)))
            doc_row = d_res.scalar_one()
            assert doc_row.status == "pending"
            assert doc_row.current_version_id is None

            v_res = await session.execute(
                select(DocumentVersion).where(DocumentVersion.id == UUID(ver_id))
            )
            ver_row = v_res.scalar_one()
            assert ver_row.status == "pending"
            assert ver_row.version_number == 1

        # 3. Run the worker for real (mock only the embedding call)
        r = get_redis()
        with patch("app.worker.ingestion._embed_chunks", new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [[0.3] * 768]
            fields = {
                "document_version_id": ver_id,
                "tenant_id": str(tenant_a_id),
                "bot_id": str(bot_id),
                "attempt": "1",
            }
            await process_one(r, "3f-msg-1", fields)

        # 4. Assert DB flipped to ready and current_version_id now points at V1
        async with tenant_session(tenant_a_id) as session:
            d_res2 = await session.execute(select(Document).where(Document.id == UUID(doc_id)))
            doc_after = d_res2.scalar_one()
            assert doc_after.status == "ready"
            assert str(doc_after.current_version_id) == ver_id

            v_res2 = await session.execute(
                select(DocumentVersion).where(DocumentVersion.id == UUID(ver_id))
            )
            ver_after = v_res2.scalar_one()
            assert ver_after.status == "ready"

        # 5. GET chunks — must serve the V1 chunks produced by the worker
        chunks_res = await client.get(
            f"/api/v1/bots/{bot_id}/documents/{doc_id}/chunks",
            headers=headers,
        )
        assert chunks_res.status_code == 200, chunks_res.text
        chunks_body = chunks_res.json()
        assert chunks_body["total"] >= 1
        assert chunks_body["chunks"][0]["document_version_id"] == ver_id


# ---------------------------------------------------------------------------
# 3g. Role enforcement: end_user is forbidden on POST and GET document endpoints
# ---------------------------------------------------------------------------


async def test_3g_end_user_cannot_upload(test_bot):
    """
    A user with role 'end_user' must receive 403 on:
      - POST  /api/v1/bots/{bot_id}/documents   (upload)
      - GET   /api/v1/bots/{bot_id}/documents   (list)
    All document endpoints declare require_role("tenant_admin"), so any other
    role must be uniformly blocked.
    """
    tenant_a_id, _, user_a_id, _, bot_id = test_bot

    # Mint an end_user token for the SAME tenant and user (only role differs)
    end_user_token = create_access_token(
        user_id=user_a_id, tenant_id=tenant_a_id, role="end_user"
    )
    end_user_headers = {"Authorization": f"Bearer {end_user_token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # POST upload must be 403
        post_res = await client.post(
            f"/api/v1/bots/{bot_id}/documents",
            headers=end_user_headers,
            files={"file": ("test.txt", b"some content", "text/plain")},
        )
        assert post_res.status_code == 403, (
            f"Expected 403 for end_user POST upload, got {post_res.status_code}: {post_res.text}"
        )

        # GET list must also be 403 (role guard applies to all document endpoints)
        get_res = await client.get(
            f"/api/v1/bots/{bot_id}/documents",
            headers=end_user_headers,
        )
        assert get_res.status_code == 403, (
            f"Expected 403 for end_user GET list, got {get_res.status_code}: {get_res.text}"
        )


# ---------------------------------------------------------------------------
# 3h. Cross-tenant bot_id is invisible (404), not 403 or 500
# ---------------------------------------------------------------------------


async def test_3h_cross_tenant_bot_id_returns_404(test_bot):
    """
    Tenant A's admin uses a bot_id that belongs to Tenant B.
    Because RLS makes Tenant B's rows invisible inside Tenant A's session,
    the bot lookup returns None and the API returns 404 — consistent with
    how every other cross-tenant row lookup behaves in this codebase.
    Specifically: must NOT be 403 (that would leak the bot's existence)
    and must NOT be 500 (which would indicate a hard error or unhandled exception).
    """
    tenant_a_id, tenant_b_id, user_a_id, user_b_id, bot_id = test_bot

    # Create a bot that belongs exclusively to Tenant B
    async with tenant_session(tenant_b_id) as session:
        tenant_b_bot = Bot(
            id=uuid.uuid4(),
            tenant_id=tenant_b_id,
            name="Tenant B Bot",
            slug=f"tenant-b-bot-{uuid.uuid4().hex[:6]}",
            widget_key_hash=f"hash_{uuid.uuid4().hex[:8]}",
            status="active",
        )
        session.add(tenant_b_bot)
        await session.flush()
        tenant_b_bot_id = tenant_b_bot.id

    # Authenticate as Tenant A's admin
    token_a = create_access_token(
        user_id=user_a_id, tenant_id=tenant_a_id, role="tenant_admin"
    )
    headers_a = {"Authorization": f"Bearer {token_a}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # GET list of documents using Tenant B's bot_id — must be 404
        res = await client.get(
            f"/api/v1/bots/{tenant_b_bot_id}/documents",
            headers=headers_a,
        )
        assert res.status_code == 404, (
            f"Expected 404 for cross-tenant bot_id, got {res.status_code}: {res.text}"
        )
