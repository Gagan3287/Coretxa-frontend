"""
Tests for Upload Validation & API Hygiene (WP-A: A1-A8).
"""
import io
import uuid
from uuid import UUID
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import select

from app.core.config import settings
from app.core.database import tenant_session
from app.core.security import create_access_token
from app.core.upload_validation import (
    UploadValidationError,
    sanitize_filename,
    validate_pdf,
    validate_upload,
)
from app.main import app
from app.models import Bot, Document, DocumentVersion

# Tests are marked per-function where async


def make_valid_pdf(text: str = "Valid sample PDF for upload validation testing.") -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(100, 700, text)
    c.showPage()
    c.save()
    return buf.getvalue()


def make_multipage_pdf(num_pages: int) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    for i in range(num_pages):
        c.drawString(100, 700, f"Page {i + 1} content in multipage document.")
        c.showPage()
    c.save()
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Unit tests: sanitize_filename (A5)
# ---------------------------------------------------------------------------


def test_sanitize_filename():
    assert sanitize_filename(None) == "document.pdf"
    assert sanitize_filename("") == "document.pdf"
    assert sanitize_filename("   ") == "document.pdf"

    # Strips path separators and traversal
    assert sanitize_filename("../../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename("..\\..\\secret.pdf") == "secret.pdf"
    assert sanitize_filename("C:\\Users\\admin\\document.pdf") == "document.pdf"
    assert sanitize_filename("/var/log/report.pdf") == "report.pdf"

    # Control chars removed
    assert sanitize_filename("report\x00with\x1fnull.pdf") == "reportwithnull.pdf"
    assert sanitize_filename("\x00\x01\x02") == "document.pdf"

    # Truncation to 255 chars
    long_name = "a" * 300 + ".pdf"
    sanitized = sanitize_filename(long_name)
    assert len(sanitized) == 255


# ---------------------------------------------------------------------------
# Unit tests: validate_upload & validate_pdf (A1-A4)
# ---------------------------------------------------------------------------


def test_validate_upload_empty_file():
    with pytest.raises(UploadValidationError) as exc_info:
        validate_upload(b"")
    assert exc_info.value.http_status == 400
    assert exc_info.value.error_code == "empty_file"


def test_validate_upload_non_pdf():
    # PNG magic bytes
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
    with pytest.raises(UploadValidationError) as exc:
        validate_upload(png_bytes)
    assert exc.value.http_status == 400
    assert exc.value.error_code == "invalid_file_format"

    # JPEG magic bytes
    jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 50
    with pytest.raises(UploadValidationError) as exc:
        validate_upload(jpeg_bytes)
    assert exc.value.http_status == 400
    assert exc.value.error_code == "invalid_file_format"

    # Plaintext
    txt_bytes = b"Hello world, this is a plain text file."
    with pytest.raises(UploadValidationError) as exc:
        validate_upload(txt_bytes)
    assert exc.value.http_status == 400
    assert exc.value.error_code == "invalid_file_format"


def test_validate_upload_corrupt_pdf():
    corrupt_pdf = b"%PDF-1.4\nInvalid corrupted stream content\n%%EOF"
    with pytest.raises(UploadValidationError) as exc:
        validate_upload(corrupt_pdf)
    assert exc.value.http_status == 400
    assert exc.value.error_code == "invalid_file_format"


def test_validate_upload_too_many_pages(monkeypatch):
    monkeypatch.setattr(settings, "MAX_PDF_PAGES", 3)
    pdf_4_pages = make_multipage_pdf(4)
    with pytest.raises(UploadValidationError) as exc:
        validate_upload(pdf_4_pages)
    assert exc.value.http_status == 400
    assert exc.value.error_code == "too_many_pages"


def test_validate_upload_valid_pdf():
    pdf = make_valid_pdf()
    content_type = validate_upload(pdf)
    assert content_type == "application/pdf"


# ---------------------------------------------------------------------------
# API endpoint tests: Rejections & Duplicate detection (A6, A7, A8)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def bot_ctx(two_tenants):
    tenant_a_id, _, user_a_id, _ = two_tenants
    async with tenant_session(tenant_a_id) as session:
        bot = Bot(
            id=uuid.uuid4(),
            tenant_id=tenant_a_id,
            name="Upload Validation Bot",
            slug=f"uv-bot-{uuid.uuid4().hex[:6]}",
            widget_key_hash=f"hash_{uuid.uuid4().hex[:8]}",
            status="active",
        )
        session.add(bot)
        await session.flush()
        bot_id = bot.id

    token = create_access_token(user_id=user_a_id, tenant_id=tenant_a_id, role="tenant_admin")
    headers = {"Authorization": f"Bearer {token}"}
    return tenant_a_id, bot_id, headers


@pytest.mark.asyncio
async def test_api_rejects_non_pdf(bot_ctx):
    tenant_id, bot_id, headers = bot_ctx
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # PNG
        res = await client.post(
            f"/api/v1/bots/{bot_id}/documents",
            headers=headers,
            files={"file": ("image.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 20, "image/png")},
        )
        assert res.status_code == 400
        assert res.json()["detail"]["error"] == "invalid_file_format"

        # JPEG
        res = await client.post(
            f"/api/v1/bots/{bot_id}/documents",
            headers=headers,
            files={"file": ("photo.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 20, "image/jpeg")},
        )
        assert res.status_code == 400
        assert res.json()["detail"]["error"] == "invalid_file_format"


@pytest.mark.asyncio
async def test_api_rejects_empty_file(bot_ctx):
    tenant_id, bot_id, headers = bot_ctx
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/bots/{bot_id}/documents",
            headers=headers,
            files={"file": ("empty.pdf", b"", "application/pdf")},
        )
        assert res.status_code == 400
        assert res.json()["detail"]["error"] == "empty_file"


@pytest.mark.asyncio
async def test_api_duplicate_content_detection(bot_ctx):
    """
    A8: Re-uploading identical file to the same document returns 409 duplicate_content
    unless force=true is provided.
    """
    tenant_id, bot_id, headers = bot_ctx
    pdf_bytes = make_valid_pdf("Identical document content for sha256 duplicate testing.")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Initial upload -> 201
        with patch("app.api.v1.documents.enqueue", new_callable=AsyncMock):
            res1 = await client.post(
                f"/api/v1/bots/{bot_id}/documents",
                headers=headers,
                files={"file": ("first.pdf", pdf_bytes, "application/pdf")},
            )
            assert res1.status_code == 201
            doc_id = res1.json()["document_id"]
            ver1_id = res1.json()["version_id"]

        # Simulate worker completing v1 -> ready
        async with tenant_session(tenant_id) as session:
            doc = (await session.execute(select(Document).where(Document.id == UUID(doc_id)))).scalar_one()
            ver = (await session.execute(select(DocumentVersion).where(DocumentVersion.id == UUID(ver1_id)))).scalar_one()
            ver.status = "ready"
            doc.status = "ready"
            doc.current_version_id = ver.id

        # 2. Re-upload same content without force -> 409 duplicate_content
        with patch("app.api.v1.documents.enqueue", new_callable=AsyncMock):
            res2 = await client.post(
                f"/api/v1/bots/{bot_id}/documents",
                headers=headers,
                data={"document_id": doc_id},
                files={"file": ("second.pdf", pdf_bytes, "application/pdf")},
            )
            assert res2.status_code == 409
            assert res2.json()["detail"]["error"] == "duplicate_content"

        # 3. Re-upload same content WITH force=True -> 201 succeeds
        with patch("app.api.v1.documents.enqueue", new_callable=AsyncMock):
            res3 = await client.post(
                f"/api/v1/bots/{bot_id}/documents",
                headers=headers,
                data={"document_id": doc_id, "force": "true"},
                files={"file": ("third.pdf", pdf_bytes, "application/pdf")},
            )
            assert res3.status_code == 201
            assert res3.json()["version_number"] == 2


@pytest.mark.asyncio
async def test_api_responses_omit_file_path(bot_ctx):
    """
    A6: file_path must never be present in API responses (upload, detail, list, chunks).
    """
    tenant_id, bot_id, headers = bot_ctx
    pdf_bytes = make_valid_pdf("Sample PDF to check schema response hygiene.")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Upload response
        with patch("app.api.v1.documents.enqueue", new_callable=AsyncMock):
            res = await client.post(
                f"/api/v1/bots/{bot_id}/documents",
                headers=headers,
                files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
            )
            assert res.status_code == 201
            body = res.json()
            assert "file_path" not in body
            doc_id = body["document_id"]

        # Detail response
        detail_res = await client.get(f"/api/v1/bots/{bot_id}/documents/{doc_id}", headers=headers)
        assert detail_res.status_code == 200
        detail_body = detail_res.json()
        assert "file_path" not in detail_body
        for v in detail_body.get("versions", []):
            assert "file_path" not in v

        # List response
        list_res = await client.get(f"/api/v1/bots/{bot_id}/documents", headers=headers)
        assert list_res.status_code == 200
        list_body = list_res.json()
        for doc in list_body.get("documents", []):
            assert "file_path" not in doc
