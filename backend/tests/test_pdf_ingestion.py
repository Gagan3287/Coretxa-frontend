import io
import uuid
from uuid import UUID
from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, DataError

from app.core.config import settings
from app.core.database import tenant_session
from app.core.security import create_access_token
from app.main import app
from app.models import Chunk, Document, DocumentVersion
from app.worker.ingestion import process_one
from app.worker.queue import DLQ_KEY, STREAM_KEY, get_redis

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# PDF Generators using ReportLab
# ---------------------------------------------------------------------------

def make_multipage_pdf() -> bytes:
    """Multi-page PDF with headings and known sentences."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    # Page 1
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "INTRODUCTION HEADING")
    c.setFont("Helvetica", 12)
    c.drawString(100, 700, "Alpha bravo charlie known sentence on page one.")
    c.drawString(100, 680, "Delta echo foxtrot second sentence in introduction.")
    c.showPage()

    # Page 2
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "METHODOLOGY HEADING")
    c.setFont("Helvetica", 12)
    c.drawString(100, 700, "Golf hotel india known sentence on page two.")
    c.showPage()

    c.save()
    return buf.getvalue()


def make_pdf_with_nul() -> bytes:
    """PDF containing a NUL byte in its text."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, pageCompression=0)
    c.setFont("Helvetica", 12)
    c.drawString(100, 700, "PLACEHOLDER_FOR_NUL_CHARACTERS")
    c.showPage()
    c.save()
    raw = buf.getvalue()
    # Inject actual NUL byte into the uncompressed stream
    target = b"PLACEHOLDER_FOR_NUL_CHARACTERS"
    replacement = b"Known sentence with " + bytes([0]) + b" nul byte embedded."
    # Pad to equal length or replace directly
    return raw.replace(target, replacement.ljust(len(target), b" "))


def make_blank_pdf() -> bytes:
    """Blank PDF with no text."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.showPage()
    c.save()
    return buf.getvalue()


def make_corrupted_pdf_with_header() -> bytes:
    """Corrupted file with a valid %PDF- header."""
    return b"%PDF-1.4\nCorrupted binary content that is invalid PDF stream garbage\n%%EOF"


# ---------------------------------------------------------------------------
# Test Bot Fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def bot_fixture(two_tenants):
    from app.models import Bot
    tenant_a_id, _, user_a_id, _ = two_tenants
    async with tenant_session(tenant_a_id) as session:
        bot = Bot(
            id=uuid.uuid4(),
            tenant_id=tenant_a_id,
            name="PDF Test Bot",
            slug=f"pdf-bot-{uuid.uuid4().hex[:6]}",
            widget_key_hash=f"hash_{uuid.uuid4().hex[:8]}",
            status="active",
        )
        session.add(bot)
        await session.flush()
        bot_id = bot.id

    token = create_access_token(user_id=user_a_id, tenant_id=tenant_a_id, role="tenant_admin")
    headers = {"Authorization": f"Bearer {token}"}
    return tenant_a_id, bot_id, headers


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_4a_multipage_pdf_real_extraction_and_metadata(bot_fixture):
    """
    (a) Multi-page PDF with headings and known sentences:
    - version ready
    - stored chunk text contains known sentences and NO %PDF, endobj, or NUL
    - chunk_metadata has page numbers and embedding model
    """
    tenant_id, bot_id, headers = bot_fixture
    r = get_redis()
    await r.flushdb()

    pdf_bytes = make_multipage_pdf()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.api.v1.documents.enqueue", new_callable=AsyncMock) as mock_enqueue:
            res = await client.post(
                f"/api/v1/bots/{bot_id}/documents",
                headers=headers,
                files={"file": ("multipage.pdf", pdf_bytes, "application/pdf")},
            )
            assert res.status_code == 201
            data = res.json()
            doc_id = UUID(data["document_id"])
            ver_id = UUID(data["version_id"])

    # Worker processes the version with only embedding client mocked
    fields = {
        "document_version_id": str(ver_id),
        "tenant_id": str(tenant_id),
        "bot_id": str(bot_id),
        "attempt": "1",
    }
    with patch("app.worker.ingestion._embed_chunks", new_callable=AsyncMock) as mock_embed:
        mock_embed.side_effect = lambda texts, **kwargs: [[0.1] * 768 for _ in texts]
        await process_one(r, "1001-0", fields)
        assert mock_embed.call_count >= 1

    # Check DB state
    async with tenant_session(tenant_id) as session:
        v_res = await session.execute(select(DocumentVersion).where(DocumentVersion.id == ver_id))
        ver = v_res.scalar_one()
        assert ver.status == "ready", f"Version failed with: {ver.error_message}"

        d_res = await session.execute(select(Document).where(Document.id == doc_id))
        doc = d_res.scalar_one()
        assert doc.status == "ready"

        c_res = await session.execute(select(Chunk).where(Chunk.document_version_id == ver_id).order_by(Chunk.chunk_index))
        chunks = c_res.scalars().all()
        assert len(chunks) >= 1

        all_content = " ".join(c.content for c in chunks)
        # Verify known sentences are present
        assert "Alpha bravo charlie known sentence on page one" in all_content
        assert "Golf hotel india known sentence on page two" in all_content

        # Verify NO raw PDF garbage reached chunk text
        assert "%PDF" not in all_content
        assert "endobj" not in all_content
        assert "\x00" not in all_content

        # Verify chunk metadata has page numbers and embedding model
        for c in chunks:
            assert "embedding_model" in c.chunk_metadata
            assert c.chunk_metadata["embedding_model"] == settings.EMBEDDING_MODEL
            assert "page_number" in c.chunk_metadata or "page_numbers" in c.chunk_metadata
            if "page_number" in c.chunk_metadata:
                assert isinstance(c.chunk_metadata["page_number"], int)
                assert c.chunk_metadata["page_number"] in [1, 2]


async def test_4b_pdf_with_nul_byte_sanitized(bot_fixture):
    """
    (b) PDF containing a NUL byte in its text:
    - stored without the NUL
    - version ready
    """
    tenant_id, bot_id, headers = bot_fixture
    r = get_redis()
    await r.flushdb()

    pdf_bytes = make_pdf_with_nul()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.api.v1.documents.enqueue", new_callable=AsyncMock):
            res = await client.post(
                f"/api/v1/bots/{bot_id}/documents",
                headers=headers,
                files={"file": ("nul.pdf", pdf_bytes, "application/pdf")},
            )
            assert res.status_code == 201
            data = res.json()
            doc_id = UUID(data["document_id"])
            ver_id = UUID(data["version_id"])

    fields = {
        "document_version_id": str(ver_id),
        "tenant_id": str(tenant_id),
        "bot_id": str(bot_id),
        "attempt": "1",
    }
    with patch("app.worker.ingestion._embed_chunks", new_callable=AsyncMock) as mock_embed:
        mock_embed.side_effect = lambda texts, **kwargs: [[0.1] * 768 for _ in texts]
        await process_one(r, "1002-0", fields)

    async with tenant_session(tenant_id) as session:
        v_res = await session.execute(select(DocumentVersion).where(DocumentVersion.id == ver_id))
        ver = v_res.scalar_one()
        assert ver.status == "ready", f"Version status should be ready but was {ver.status}: {ver.error_message}"

        c_res = await session.execute(select(Chunk).where(Chunk.document_version_id == ver_id))
        chunks = c_res.scalars().all()
        assert len(chunks) >= 1
        for c in chunks:
            assert "\x00" not in c.content


async def test_4c_blank_pdf_fails_gate_no_embeddings(bot_fixture):
    """
    (c) Blank or image-only PDF with no text:
    - failed with "No extractable text in this PDF (scanned or image-only PDFs are not supported yet)"
    - embedding client called ZERO times
    """
    tenant_id, bot_id, headers = bot_fixture
    r = get_redis()
    await r.flushdb()

    pdf_bytes = make_blank_pdf()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.api.v1.documents.enqueue", new_callable=AsyncMock):
            res = await client.post(
                f"/api/v1/bots/{bot_id}/documents",
                headers=headers,
                files={"file": ("blank.pdf", pdf_bytes, "application/pdf")},
            )
            assert res.status_code == 201
            ver_id = UUID(res.json()["version_id"])

    fields = {
        "document_version_id": str(ver_id),
        "tenant_id": str(tenant_id),
        "bot_id": str(bot_id),
        "attempt": "1",
    }
    with patch("app.worker.ingestion._embed_chunks", new_callable=AsyncMock) as mock_embed:
        await process_one(r, "1003-0", fields)
        assert mock_embed.call_count == 0, f"Embedding client was called {mock_embed.call_count} times; expected 0"

    async with tenant_session(tenant_id) as session:
        v_res = await session.execute(select(DocumentVersion).where(DocumentVersion.id == ver_id))
        ver = v_res.scalar_one()
        assert ver.status == "failed"
        assert "No extractable text in this PDF (scanned or image-only PDFs are not supported yet)" in (ver.error_message or "")


async def test_4d_corrupted_pdf_with_header_fails_zero_embeddings(bot_fixture):
    """
    (d) Corrupted file with a valid %PDF- header:
    - failed, no retries, embedding client called zero times
    """
    tenant_id, bot_id, headers = bot_fixture
    r = get_redis()
    await r.flushdb()

    pdf_bytes = make_corrupted_pdf_with_header()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.api.v1.documents.enqueue", new_callable=AsyncMock), \
             patch("app.api.v1.documents.validate_upload", return_value="application/pdf"):
            res = await client.post(
                f"/api/v1/bots/{bot_id}/documents",
                headers=headers,
                files={"file": ("corrupt.pdf", pdf_bytes, "application/pdf")},
            )
            assert res.status_code == 201
            ver_id = UUID(res.json()["version_id"])

    fields = {
        "document_version_id": str(ver_id),
        "tenant_id": str(tenant_id),
        "bot_id": str(bot_id),
        "attempt": "1",
    }
    with patch("app.worker.ingestion._embed_chunks", new_callable=AsyncMock) as mock_embed, \
         patch("app.worker.ingestion.enqueue", new_callable=AsyncMock) as mock_enqueue:
        await process_one(r, "1004-0", fields)
        assert mock_embed.call_count == 0
        # Should NOT retry: enqueue should NOT be called for attempt 2
        assert mock_enqueue.call_count == 0

    async with tenant_session(tenant_id) as session:
        v_res = await session.execute(select(DocumentVersion).where(DocumentVersion.id == ver_id))
        ver = v_res.scalar_one()
        assert ver.status == "failed"


async def test_retry_classification_data_error_vs_connection_error(bot_fixture, tmp_path):
    """
    Deterministic error (DataError) gets 1 attempt only and fails immediately.
    Transient error (ConnectionError) is retried.
    """
    tenant_id, bot_id, _ = bot_fixture
    r = get_redis()
    await r.flushdb()

    # Create dummy text files
    txt_file = tmp_path / "valid.txt"
    txt_file.write_text("Valid text content for testing error classifications in worker.")

    # 1. Deterministic DataError
    async with tenant_session(tenant_id) as session:
        doc1 = Document(id=uuid.uuid4(), tenant_id=tenant_id, bot_id=bot_id, original_filename="data_err.txt", status="pending")
        ver1 = DocumentVersion(id=uuid.uuid4(), tenant_id=tenant_id, bot_id=bot_id, document_id=doc1.id, version_number=1, file_path=str(txt_file), status="pending")
        session.add_all([doc1, ver1])
        await session.flush()
        ver1_id = ver1.id

    fields1 = {"document_version_id": str(ver1_id), "tenant_id": str(tenant_id), "bot_id": str(bot_id), "attempt": "1"}
    with patch("app.worker.ingestion._embed_chunks", side_effect=DataError("INSERT ...", {}, Exception("CharacterNotInRepertoireError: 0x00"))), \
         patch("app.worker.ingestion.enqueue", new_callable=AsyncMock) as mock_enqueue:
        await process_one(r, "2001-0", fields1)
        # Must not re-enqueue for attempt 2
        assert mock_enqueue.call_count == 0

    async with tenant_session(tenant_id) as session:
        v1 = (await session.execute(select(DocumentVersion).where(DocumentVersion.id == ver1_id))).scalar_one()
        assert v1.status == "failed"

    # 2. Transient ConnectionError
    async with tenant_session(tenant_id) as session:
        doc2 = Document(id=uuid.uuid4(), tenant_id=tenant_id, bot_id=bot_id, original_filename="conn_err.txt", status="pending")
        ver2 = DocumentVersion(id=uuid.uuid4(), tenant_id=tenant_id, bot_id=bot_id, document_id=doc2.id, version_number=1, file_path=str(txt_file), status="pending")
        session.add_all([doc2, ver2])
        await session.flush()
        ver2_id = ver2.id

    fields2 = {"document_version_id": str(ver2_id), "tenant_id": str(tenant_id), "bot_id": str(bot_id), "attempt": "1"}
    with patch("app.worker.ingestion._embed_chunks", side_effect=ConnectionError("Connection lost")), \
         patch("asyncio.sleep", new_callable=AsyncMock), \
         patch("app.worker.ingestion.enqueue", new_callable=AsyncMock) as mock_enqueue:
        await process_one(r, "2002-0", fields2)
        # Transient error must be retried: enqueue called for attempt 2
        assert mock_enqueue.call_count == 1
        call_kwargs = mock_enqueue.call_args[1]
        assert call_kwargs["attempt"] == 2


async def test_dbapi_error_log_hygiene_redacts_parameters_and_secrets(bot_fixture, tmp_path, caplog):
    """
    Raise a DBAPIError whose message contains a "[parameters: ...]" section with a secret sentence,
    and assert that the stored error_message and the captured logs do not contain that sentence.
    """
    import logging
    tenant_id, bot_id, _ = bot_fixture
    r = get_redis()
    await r.flushdb()

    txt_file = tmp_path / "hygiene.txt"
    txt_file.write_text("Hygiene testing content.")

    async with tenant_session(tenant_id) as session:
        doc = Document(id=uuid.uuid4(), tenant_id=tenant_id, bot_id=bot_id, original_filename="hygiene.txt", status="pending")
        ver = DocumentVersion(id=uuid.uuid4(), tenant_id=tenant_id, bot_id=bot_id, document_id=doc.id, version_number=1, file_path=str(txt_file), status="pending")
        session.add_all([doc, ver])
        await session.flush()
        ver_id = ver.id
        doc_id = doc.id

    secret_sentence = "TOP_SECRET_PROPRIETARY_SENTENCE_THAT_MUST_NEVER_LEAK"
    error_msg = f"SELECT * FROM chunks WHERE [parameters: {{'secret': '{secret_sentence}', 'key': 'AIzaSyFakeKey1234567890123456789012345'}}]"
    
    # Construct a DBAPIError with parameters in message
    dbapi_err = DBAPIError("SELECT ...", {}, Exception(error_msg))

    fields = {"document_version_id": str(ver_id), "tenant_id": str(tenant_id), "bot_id": str(bot_id), "attempt": "3"}

    with patch("app.worker.ingestion._embed_chunks", new_callable=AsyncMock) as mock_embed, \
         patch("app.worker.ingestion._apply_success", side_effect=dbapi_err), \
         caplog.at_level(logging.DEBUG):
        mock_embed.return_value = [[0.1] * 768]
        await process_one(r, "3001-0", fields)

    # Verify DB state
    async with tenant_session(tenant_id) as session:
        v = (await session.execute(select(DocumentVersion).where(DocumentVersion.id == ver_id))).scalar_one()
        d = (await session.execute(select(Document).where(Document.id == doc_id))).scalar_one()

        assert v.status == "failed"
        assert v.error_message is not None
        assert secret_sentence not in v.error_message
        assert "[parameters:" not in v.error_message.lower()
        assert "AIzaSy" not in v.error_message

        assert d.status == "failed"
        assert d.error_message is not None
        assert secret_sentence not in d.error_message
        assert "[parameters:" not in d.error_message.lower()

    # Verify captured logs
    assert secret_sentence not in caplog.text
    assert "AIzaSy" not in caplog.text


async def test_in_process_db_write_retry_does_not_reembed(bot_fixture, tmp_path):
    """
    A transient failure of the DB write must not re-embed: keep the computed
    vectors in memory and retry the transaction in-process instead of re-enqueueing.
    """
    tenant_id, bot_id, _ = bot_fixture
    r = get_redis()
    await r.flushdb()

    txt_file = tmp_path / "retry_db.txt"
    txt_file.write_text("Text for testing in-process DB retry.")

    async with tenant_session(tenant_id) as session:
        doc = Document(id=uuid.uuid4(), tenant_id=tenant_id, bot_id=bot_id, original_filename="retry_db.txt", status="pending")
        ver = DocumentVersion(id=uuid.uuid4(), tenant_id=tenant_id, bot_id=bot_id, document_id=doc.id, version_number=1, file_path=str(txt_file), status="pending")
        session.add_all([doc, ver])
        await session.flush()
        ver_id = ver.id
        doc_id = doc.id

    fields = {"document_version_id": str(ver_id), "tenant_id": str(tenant_id), "bot_id": str(bot_id), "attempt": "1"}

    from app.worker.ingestion import _apply_success as real_apply_success
    call_count = 0

    async def flaky_apply_success(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("Transient DB connection drop")
        return await real_apply_success(*args, **kwargs)

    with patch("app.worker.ingestion._embed_chunks", new_callable=AsyncMock) as mock_embed, \
         patch("app.worker.ingestion._apply_success", side_effect=flaky_apply_success), \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
         patch("app.worker.ingestion.enqueue", new_callable=AsyncMock) as mock_enqueue:
        mock_embed.return_value = [[0.1] * 768]
        await process_one(r, "4001-0", fields)

        # _embed_chunks called EXACTLY ONCE
        assert mock_embed.call_count == 1
        # DB write retried in-process (called twice: 1 fail + 1 success)
        assert call_count == 2
        # Did NOT re-enqueue to redis stream
        assert mock_enqueue.call_count == 0

    async with tenant_session(tenant_id) as session:
        v = (await session.execute(select(DocumentVersion).where(DocumentVersion.id == ver_id))).scalar_one()
        assert v.status == "ready"

