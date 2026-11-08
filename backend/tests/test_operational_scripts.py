"""
Unit tests for operational scripts (WP-E):
- scripts/inspect_queue.py (E2 / E5)
- scripts/requeue_version.py (E3)
- scripts/diagnose_embedding_quota.py (E4)
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.diagnose_embedding_quota import run_diagnostics
from scripts.inspect_queue import inspect_queue
from scripts.requeue_version import requeue_version


# ===========================================================================
# 1. scripts/inspect_queue.py
# ===========================================================================

@pytest.mark.asyncio
async def test_inspect_queue_success():
    """inspect_queue reports stream length, groups, pending, and DLQ entries."""
    mock_redis = MagicMock()
    mock_redis.xlen = AsyncMock(side_effect=[5, 2])  # primary stream=5, dlq=2
    mock_redis.xinfo_groups = AsyncMock(return_value=[
        {"name": "ingestion_workers", "consumers": 1, "pending": 0}
    ])
    mock_redis.xpending = AsyncMock(return_value={"pending": 0, "min": None, "max": None, "consumers": []})
    mock_redis.xrevrange = AsyncMock(return_value=[
        (b"1700000000000-0", {b"document_version_id": b"ver-1", b"error": b"boom"}),
        (b"1700000000001-0", {b"document_version_id": b"ver-2", b"error": b"timeout"}),
    ])

    with patch("scripts.inspect_queue.get_redis", return_value=mock_redis):
        exit_code = await inspect_queue(limit=5)
        assert exit_code == 0

    assert mock_redis.xlen.await_count == 2
    mock_redis.xrevrange.assert_awaited_once()


@pytest.mark.asyncio
async def test_inspect_queue_handles_errors():
    """inspect_queue catches connection errors gracefully and returns 0."""
    mock_redis = MagicMock()
    mock_redis.xlen = AsyncMock(side_effect=Exception("Redis connection refused"))

    with patch("scripts.inspect_queue.get_redis", return_value=mock_redis):
        exit_code = await inspect_queue(limit=5)
        assert exit_code == 0


# ===========================================================================
# 2. scripts/requeue_version.py
# ===========================================================================

@pytest.mark.asyncio
async def test_requeue_version_with_explicit_ids():
    """requeue_version resets document and version status and enqueues to Redis."""
    version_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    bot_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    mock_ver = MagicMock()
    mock_ver.id = version_id
    mock_ver.document_id = doc_id
    mock_ver.status = "failed"
    mock_ver.error_message = "Previous error"

    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.status = "failed"
    mock_doc.error_message = "Previous error"

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=mock_ver)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=mock_doc)),
    ])

    class FakeSessionContext:
        async def __aenter__(self):
            return mock_session
        async def __aexit__(self, *args):
            pass

    mock_redis = MagicMock()

    with (
        patch("scripts.requeue_version.get_redis", return_value=mock_redis),
        patch("scripts.requeue_version.tenant_session", return_value=FakeSessionContext()),
        patch("scripts.requeue_version.enqueue", new_callable=AsyncMock, return_value="1-0") as mock_enqueue,
    ):
        exit_code = await requeue_version(version_id, tenant_id=tenant_id, bot_id=bot_id)
        assert exit_code == 0

    # Status must be reset to pending
    assert mock_ver.status == "pending"
    assert mock_ver.error_message is None
    assert mock_doc.status == "pending"
    assert mock_doc.error_message is None

    mock_enqueue.assert_awaited_once_with(
        mock_redis,
        document_version_id=version_id,
        tenant_id=tenant_id,
        bot_id=bot_id,
        attempt=1,
    )


@pytest.mark.asyncio
async def test_requeue_version_auto_lookup():
    """requeue_version looks up tenant_id and bot_id via platform_session if omitted."""
    version_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    bot_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    lookup_ver = MagicMock()
    lookup_ver.id = version_id
    lookup_ver.tenant_id = tenant_id
    lookup_ver.bot_id = bot_id
    lookup_ver.document_id = doc_id

    mock_ver = MagicMock()
    mock_ver.document_id = doc_id
    mock_doc = MagicMock()

    platform_session_mock = AsyncMock()
    platform_session_mock.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=lookup_ver))
    )

    tenant_session_mock = AsyncMock()
    tenant_session_mock.execute = AsyncMock(side_effect=[
        MagicMock(scalar_one_or_none=MagicMock(return_value=mock_ver)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=mock_doc)),
    ])

    class FakeContext:
        def __init__(self, s):
            self.s = s
        async def __aenter__(self):
            return self.s
        async def __aexit__(self, *args):
            pass

    with (
        patch("scripts.requeue_version.get_redis", return_value=MagicMock()),
        patch("scripts.requeue_version.platform_session", return_value=FakeContext(platform_session_mock)),
        patch("scripts.requeue_version.tenant_session", return_value=FakeContext(tenant_session_mock)),
        patch("scripts.requeue_version.enqueue", new_callable=AsyncMock, return_value="1-0"),
    ):
        exit_code = await requeue_version(version_id)
        assert exit_code == 0

    assert mock_ver.status == "pending"
    assert mock_doc.status == "pending"


@pytest.mark.asyncio
async def test_requeue_version_not_found():
    """requeue_version returns 1 if version is not in DB."""
    version_id = uuid.uuid4()

    platform_session_mock = AsyncMock()
    platform_session_mock.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )

    class FakeContext:
        async def __aenter__(self):
            return platform_session_mock
        async def __aexit__(self, *args):
            pass

    with (
        patch("scripts.requeue_version.get_redis", return_value=MagicMock()),
        patch("scripts.requeue_version.platform_session", return_value=FakeContext()),
    ):
        exit_code = await requeue_version(version_id)
        assert exit_code == 1


# ===========================================================================
# 3. scripts/diagnose_embedding_quota.py
# ===========================================================================

@pytest.mark.asyncio
async def test_diagnose_embedding_quota_missing_key():
    """run_diagnostics returns 1 if no key is supplied and settings has none."""
    with patch("scripts.diagnose_embedding_quota.settings.GOOGLE_API_KEY", ""):
        exit_code = await run_diagnostics(api_key=None)
        assert exit_code == 1


@pytest.mark.asyncio
async def test_diagnose_embedding_quota_success():
    """run_diagnostics returns 0 upon successful vector embedding."""
    fake_vectors = [[0.1] * 768, [0.2] * 768]
    with patch("scripts.diagnose_embedding_quota.embed_texts", new_callable=AsyncMock, return_value=fake_vectors):
        exit_code = await run_diagnostics(api_key="AIzaSyDummyKeyForDiagnosticsTest1234")
        assert exit_code == 0


@pytest.mark.asyncio
async def test_diagnose_embedding_quota_handles_failure():
    """run_diagnostics returns 1 and logs failure if API raises error."""
    with patch("scripts.diagnose_embedding_quota.embed_texts", new_callable=AsyncMock, side_effect=RuntimeError("Quota 429")):
        exit_code = await run_diagnostics(api_key="AIzaSyDummyKeyForDiagnosticsTest1234")
        assert exit_code == 1
