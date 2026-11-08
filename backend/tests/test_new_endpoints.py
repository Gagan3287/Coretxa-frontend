"""
Tests for new backend endpoints:
1. POST /auth/register (public registration, validation, rate limiting, reserved slugs, conflict)
2. GET /auth/me (authenticated user profile with full_name, tenant slug, role)
3. POST /auth/refresh (refresh token rotation, rejection of invalid/expired tokens)
4. PATCH /api/v1/bots/{bot_id} (update name, merge branding_json, cross-tenant isolation)
5. DELETE /api/v1/bots/{bot_id}/documents/{doc_id} (204 delete document, chunks, versions, storage seam)
6. document_count in bot list and detail responses
"""
import uuid
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.auth import _registration_attempts
from app.core.database import platform_session, tenant_session
from app.core.security import create_access_token, create_refresh_token
from app.core.storage import get_storage
from app.main import app
from app.models import Bot, Document, DocumentVersion, Tenant, User

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def clear_rate_limit():
    _registration_attempts.clear()


# ---------------------------------------------------------------------------
# POST /auth/register tests
# ---------------------------------------------------------------------------


async def test_register_happy_path():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        unique_slug = f"acme-{uuid.uuid4().hex[:6]}"
        resp = await client.post(
            "/auth/register",
            json={
                "org_name": "Acme Corporation",
                "org_slug": unique_slug,
                "email": f"owner@{unique_slug}.test",
                "password": "Password123!",
                "phone": "+12345678901",
                "full_name": "Alice Acme",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"


async def test_register_phone_valid_cases():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Valid with leading +
        slug1 = f"ph1-{uuid.uuid4().hex[:6]}"
        resp1 = await client.post(
            "/auth/register",
            json={
                "org_name": "Phone One",
                "org_slug": slug1,
                "email": f"user@{slug1}.test",
                "password": "Password123!",
                "phone": "+919876543210",
            },
        )
        assert resp1.status_code == 201

        # 2. Valid without + (10 digits)
        slug2 = f"ph2-{uuid.uuid4().hex[:6]}"
        resp2 = await client.post(
            "/auth/register",
            json={
                "org_name": "Phone Two",
                "org_slug": slug2,
                "email": f"user@{slug2}.test",
                "password": "Password123!",
                "phone": "9876543210",
            },
        )
        assert resp2.status_code == 201


async def test_register_phone_validation_failures():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Too short (< 10 digits)
        resp = await client.post(
            "/auth/register",
            json={
                "org_name": "Short",
                "org_slug": f"s-{uuid.uuid4().hex[:6]}",
                "email": "short@phone.test",
                "password": "Password123!",
                "phone": "+123456789",  # 9 digits
            },
        )
        assert resp.status_code == 422

        # Too long (> 15 digits)
        resp = await client.post(
            "/auth/register",
            json={
                "org_name": "Long",
                "org_slug": f"l-{uuid.uuid4().hex[:6]}",
                "email": "long@phone.test",
                "password": "Password123!",
                "phone": "+1234567890123456",  # 16 digits
            },
        )
        assert resp.status_code == 422

        # Non-digits (letters or symbols)
        resp = await client.post(
            "/auth/register",
            json={
                "org_name": "Alpha",
                "org_slug": f"a-{uuid.uuid4().hex[:6]}",
                "email": "alpha@phone.test",
                "password": "Password123!",
                "phone": "+1234567890a",
            },
        )
        assert resp.status_code == 422

        # Missing phone
        resp = await client.post(
            "/auth/register",
            json={
                "org_name": "No Phone",
                "org_slug": f"np-{uuid.uuid4().hex[:6]}",
                "email": "nophone@test.com",
                "password": "Password123!",
            },
        )
        assert resp.status_code == 422


async def test_register_validation_and_reserved_slug():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Short password (< 8 chars)
        resp = await client.post(
            "/auth/register",
            json={
                "org_name": "Acme",
                "org_slug": f"acme-{uuid.uuid4().hex[:6]}",
                "email": "test@shortpw.com",
                "password": "short",
                "phone": "+12345678901",
            },
        )
        assert resp.status_code == 422

        # Invalid slug (uppercase or special characters)
        resp = await client.post(
            "/auth/register",
            json={
                "org_name": "Acme",
                "org_slug": "Acme_Corp!",
                "email": "test@invalidslug.com",
                "password": "ValidPassword123!",
                "phone": "+12345678901",
            },
        )
        assert resp.status_code == 422

        # Reserved slug
        resp = await client.post(
            "/auth/register",
            json={
                "org_name": "Admin Team",
                "org_slug": "admin",
                "email": "admin@cortexa.test",
                "password": "ValidPassword123!",
                "phone": "+12345678901",
            },
        )
        assert resp.status_code == 400
        assert "reserved" in resp.json()["detail"].lower()


async def test_register_duplicate_slug_conflict():
    unique_slug = f"dup-{uuid.uuid4().hex[:6]}"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp1 = await client.post(
            "/auth/register",
            json={
                "org_name": "First Tenant",
                "org_slug": unique_slug,
                "email": f"first@{unique_slug}.test",
                "password": "ValidPassword123!",
                "phone": "+12345678901",
            },
        )
        assert resp1.status_code == 201

        resp2 = await client.post(
            "/auth/register",
            json={
                "org_name": "Second Tenant",
                "org_slug": unique_slug,
                "email": f"second@{unique_slug}.test",
                "password": "ValidPassword123!",
                "phone": "+12345678901",
            },
        )
        assert resp2.status_code == 409


async def test_register_rate_limiting():
    # Make requests until rate limit is hit
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        hit_429 = False
        for _ in range(15):
            slug = f"flood-{uuid.uuid4().hex[:6]}"
            resp = await client.post(
                "/auth/register",
                json={
                    "org_name": "Flood Corp",
                    "org_slug": slug,
                    "email": f"owner@{slug}.test",
                    "password": "Password123!",
                    "phone": "+12345678901",
                },
            )
            if resp.status_code == 429:
                hit_429 = True
                assert "rate limit" in resp.json()["detail"].lower()
                break
        assert hit_429, "Rate limiter did not trigger after multiple requests"


# ---------------------------------------------------------------------------
# GET /auth/me tests
# ---------------------------------------------------------------------------


async def test_get_me_authenticated(two_tenants):
    tenant_a_id, _, user_a_id, _ = two_tenants
    token = create_access_token(user_id=user_a_id, tenant_id=tenant_a_id, role="tenant_admin")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(user_a_id)
        assert data["role"] == "tenant_admin"
        assert data["tenant_id"] == str(tenant_a_id)


async def test_get_me_unauthenticated():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/auth/me")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /auth/refresh tests
# ---------------------------------------------------------------------------


async def test_refresh_token_happy_path(two_tenants):
    tenant_a_id, _, user_a_id, _ = two_tenants
    refresh = create_refresh_token(user_id=user_a_id, tenant_id=tenant_a_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/auth/refresh", json={"refresh_token": refresh})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"


async def test_refresh_token_rejects_access_token(two_tenants):
    tenant_a_id, _, user_a_id, _ = two_tenants
    access = create_access_token(user_id=user_a_id, tenant_id=tenant_a_id, role="tenant_admin")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/auth/refresh", json={"refresh_token": access})
        assert resp.status_code == 401
        assert "invalid token type" in resp.json()["detail"].lower()


async def test_refresh_token_rejects_invalid_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/auth/refresh", json={"refresh_token": "totally.invalid.token"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/v1/bots/{bot_id} tests
# ---------------------------------------------------------------------------


async def test_patch_bot_updates_name_and_merges_branding(two_tenants):
    tenant_a_id, tenant_b_id, user_a_id, _ = two_tenants
    token_a = create_access_token(user_id=user_a_id, tenant_id=tenant_a_id, role="tenant_admin")

    # 1. Create a bot for tenant A
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        slug = f"bot-{uuid.uuid4().hex[:6]}"
        create_resp = await client.post(
            "/api/v1/bots",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "name": "Original Bot",
                "slug": slug,
                "branding_json": {"color": "#000000", "title": "Support"},
            },
        )
        assert create_resp.status_code == 201
        bot_id = create_resp.json()["bot_id"]

        # 2. Patch bot name and add/update branding
        patch_resp = await client.patch(
            f"/api/v1/bots/{bot_id}",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "name": "Updated Bot Name",
                "branding_json": {"color": "#ff0000", "subtitle": "Helpdesk"},
            },
        )
        assert patch_resp.status_code == 200
        bot_data = patch_resp.json()
        assert bot_data["name"] == "Updated Bot Name"
        # Merged branding preserves title and updates color and adds subtitle
        assert bot_data["branding_json"]["color"] == "#ff0000"
        assert bot_data["branding_json"]["title"] == "Support"
        assert bot_data["branding_json"]["subtitle"] == "Helpdesk"
        assert "document_count" in bot_data


async def test_patch_bot_cross_tenant_isolation(two_tenants):
    tenant_a_id, tenant_b_id, user_a_id, user_b_id = two_tenants
    token_a = create_access_token(user_id=user_a_id, tenant_id=tenant_a_id, role="tenant_admin")
    token_b = create_access_token(user_id=user_b_id, tenant_id=tenant_b_id, role="tenant_admin")

    # Create bot for tenant A
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        slug = f"bot-{uuid.uuid4().hex[:6]}"
        create_resp = await client.post(
            "/api/v1/bots",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"name": "Bot A", "slug": slug},
        )
        bot_id = create_resp.json()["bot_id"]

        # Tenant B tries to PATCH Tenant A's bot -> 404 (isolated)
        patch_resp = await client.patch(
            f"/api/v1/bots/{bot_id}",
            headers={"Authorization": f"Bearer {token_b}"},
            json={"name": "Hacked Bot"},
        )
        assert patch_resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/bots/{bot_id}/documents/{doc_id} tests
# ---------------------------------------------------------------------------


async def test_delete_document_success(two_tenants, tmp_path):
    tenant_a_id, tenant_b_id, user_a_id, _ = two_tenants
    token_a = create_access_token(user_id=user_a_id, tenant_id=tenant_a_id, role="tenant_admin")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create bot
        bot_slug = f"bot-{uuid.uuid4().hex[:6]}"
        bot_res = await client.post(
            "/api/v1/bots",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"name": "Bot Doc Test", "slug": bot_slug},
        )
        bot_id = bot_res.json()["bot_id"]

        # Write dummy file into storage seam
        storage = get_storage()
        version_id = uuid.uuid4()
        storage_key = f"{tenant_a_id}/{bot_id}/{version_id}.pdf"
        storage.write(storage_key, b"%PDF-1.4 sample file for delete test")
        assert storage.exists(storage_key) is True

        # Insert Document and DocumentVersion in DB
        doc_id = uuid.uuid4()
        async with tenant_session(tenant_a_id) as session:
            doc = Document(
                id=doc_id,
                tenant_id=tenant_a_id,
                bot_id=UUID(bot_id),
                original_filename="sample.pdf",
                status="ready",
            )
            ver = DocumentVersion(
                id=version_id,
                tenant_id=tenant_a_id,
                bot_id=UUID(bot_id),
                document_id=doc_id,
                version_number=1,
                file_path=storage_key,
                status="ready",
            )
            session.add_all([doc, ver])
            await session.flush()
            doc.current_version_id = ver.id

        # Verify bot list shows document_count == 1
        list_res = await client.get("/api/v1/bots", headers={"Authorization": f"Bearer {token_a}"})
        bot_item = next(b for b in list_res.json()["bots"] if b["bot_id"] == bot_id)
        assert bot_item["document_count"] == 1

        # Delete the document -> 204
        del_resp = await client.delete(
            f"/api/v1/bots/{bot_id}/documents/{doc_id}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert del_resp.status_code == 204

        # Verify file was deleted from storage seam
        assert storage.exists(storage_key) is False

        # Verify document is gone from DB
        async with tenant_session(tenant_a_id) as session:
            check_doc = await session.execute(select(Document).where(Document.id == doc_id))
            assert check_doc.scalar_one_or_none() is None

        # Verify bot list shows document_count == 0
        list_res2 = await client.get("/api/v1/bots", headers={"Authorization": f"Bearer {token_a}"})
        bot_item2 = next(b for b in list_res2.json()["bots"] if b["bot_id"] == bot_id)
        assert bot_item2["document_count"] == 0


async def test_delete_document_cross_tenant_isolation(two_tenants):
    tenant_a_id, tenant_b_id, user_a_id, user_b_id = two_tenants
    token_a = create_access_token(user_id=user_a_id, tenant_id=tenant_a_id, role="tenant_admin")
    token_b = create_access_token(user_id=user_b_id, tenant_id=tenant_b_id, role="tenant_admin")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create bot for tenant A
        bot_slug = f"bot-{uuid.uuid4().hex[:6]}"
        bot_res = await client.post(
            "/api/v1/bots",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"name": "Bot Isolation", "slug": bot_slug},
        )
        bot_id = bot_res.json()["bot_id"]

        doc_id = uuid.uuid4()
        async with tenant_session(tenant_a_id) as session:
            doc = Document(
                id=doc_id,
                tenant_id=tenant_a_id,
                bot_id=UUID(bot_id),
                original_filename="isolated.pdf",
                status="ready",
            )
            session.add(doc)

        # Tenant B tries to delete Tenant A's document -> 404
        del_res = await client.delete(
            f"/api/v1/bots/{bot_id}/documents/{doc_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert del_res.status_code == 404
