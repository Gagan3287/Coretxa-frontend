"""
Unit tests for the ingestion worker's resilience logic (items 3 & 4).

These tests do NOT require a real Redis connection or database — all external
calls are mocked.  They exercise:

  - TimeoutError inside the read loop → warning logged, backoff sleep, retry
  - ConnectionError inside the read loop → same path
  - Backoff resets to 1 s after a successful read
  - CancelledError propagates cleanly (no swallowing)
  - Empty XREADGROUP result (blocked timeout) → loop continues without
    calling process_one
  - process_one is called when a message IS returned

Design note: run_worker() is an infinite loop.  Each test drives it for a
controlled number of iterations by programming the mock to raise
asyncio.CancelledError on the Nth call to xreadgroup, which lets the loop
exit cleanly while we inspect side-effects from earlier iterations.
"""
from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
import redis.exceptions as redis_exc

from app.worker.ingestion import (
    _BACKOFF_INITIAL,
    _BACKOFF_MAX,
    run_worker,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_MSG = [
    (b"ingestion", [(b"1-0", {"document_version_id": "00000000-0000-0000-0000-000000000001",
                               "tenant_id": "00000000-0000-0000-0000-000000000002",
                               "bot_id": "00000000-0000-0000-0000-000000000003",
                               "attempt": "1"})])
]


def _make_redis_mock(xreadgroup_side_effect):
    """Return a mock Redis client with xreadgroup programmed as given."""
    r = MagicMock()
    r.xreadgroup = AsyncMock(side_effect=xreadgroup_side_effect)
    r.xgroup_create = AsyncMock(return_value=True)
    return r


# ---------------------------------------------------------------------------
# Test: TimeoutError is caught, warning logged, backoff sleep, retry
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_timeout_error_caught_and_retried(caplog):
    """
    Sequence:
      call 1 → TimeoutError
      call 2 → CancelledError  (exits the loop)

    Assert:
      - Warning was logged containing 'TimeoutError'
      - asyncio.sleep was called once with _BACKOFF_INITIAL (1 s)
      - The loop did NOT crash (CancelledError propagates, nothing else)
    """
    side_effects = [
        redis_exc.TimeoutError("Timeout reading from host:6379"),
        asyncio.CancelledError(),
    ]
    mock_r = _make_redis_mock(side_effects)

    with (
        patch("app.worker.ingestion.get_redis", return_value=mock_r),
        patch("app.worker.ingestion.ensure_consumer_group", new_callable=AsyncMock),
        patch("app.worker.ingestion.process_one", new_callable=AsyncMock),
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        caplog.at_level(logging.WARNING, logger="app.worker.ingestion"),
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_worker()

    # Warning was emitted
    assert any("TimeoutError" in r.message for r in caplog.records), (
        f"Expected 'TimeoutError' in logs, got: {[r.message for r in caplog.records]}"
    )
    # Backoff sleep was called with the initial value
    mock_sleep.assert_any_call(_BACKOFF_INITIAL)


# ---------------------------------------------------------------------------
# Test: ConnectionError is caught and retried (same code path as TimeoutError)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_connection_error_caught_and_retried(caplog):
    """
    Sequence:
      call 1 → ConnectionError
      call 2 → CancelledError

    Assert: 'ConnectionError' in warning log, backoff sleep fired.
    """
    side_effects = [
        redis_exc.ConnectionError("Connection refused"),
        asyncio.CancelledError(),
    ]
    mock_r = _make_redis_mock(side_effects)

    with (
        patch("app.worker.ingestion.get_redis", return_value=mock_r),
        patch("app.worker.ingestion.ensure_consumer_group", new_callable=AsyncMock),
        patch("app.worker.ingestion.process_one", new_callable=AsyncMock),
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        caplog.at_level(logging.WARNING, logger="app.worker.ingestion"),
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_worker()

    assert any("ConnectionError" in r.message for r in caplog.records)
    mock_sleep.assert_any_call(_BACKOFF_INITIAL)


# ---------------------------------------------------------------------------
# Test: backoff resets to 1 s after a successful read
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_backoff_resets_after_successful_read():
    """
    Sequence:
      call 1 → TimeoutError          (backoff advances to 2 s)
      call 2 → [] (empty, no msgs)   (successful read → backoff resets to 1 s)
      call 3 → TimeoutError          (next backoff must be 1 s, NOT 2 s)
      call 4 → CancelledError

    Assert: asyncio.sleep was called with 1 s TWICE (once per TimeoutError),
            proving the reset happened.
    """
    side_effects = [
        redis_exc.TimeoutError("timeout"),
        [],                               # successful empty read
        redis_exc.TimeoutError("timeout"),
        asyncio.CancelledError(),
    ]
    mock_r = _make_redis_mock(side_effects)
    sleep_calls: list[float] = []

    async def _fake_sleep(secs):
        sleep_calls.append(secs)

    with (
        patch("app.worker.ingestion.get_redis", return_value=mock_r),
        patch("app.worker.ingestion.ensure_consumer_group", new_callable=AsyncMock),
        patch("app.worker.ingestion.process_one", new_callable=AsyncMock),
        patch("asyncio.sleep", side_effect=_fake_sleep),
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_worker()

    # Both backoff sleeps should be 1 s (initial), NOT 1 s then 2 s
    assert sleep_calls == [_BACKOFF_INITIAL, _BACKOFF_INITIAL], (
        f"Expected two 1 s sleeps; got {sleep_calls}"
    )


# ---------------------------------------------------------------------------
# Test: empty XREADGROUP result → loop continues, process_one NOT called
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_result_skips_process_one():
    """
    Sequence:
      call 1 → []             (blocked read timed out, nothing new)
      call 2 → CancelledError

    Assert: process_one was never called.
    """
    side_effects = [[], asyncio.CancelledError()]
    mock_r = _make_redis_mock(side_effects)

    with (
        patch("app.worker.ingestion.get_redis", return_value=mock_r),
        patch("app.worker.ingestion.ensure_consumer_group", new_callable=AsyncMock),
        patch("app.worker.ingestion.process_one", new_callable=AsyncMock) as mock_process,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_worker()

    mock_process.assert_not_called()


# ---------------------------------------------------------------------------
# Test: message present → process_one called with correct args
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_message_dispatched_to_process_one():
    """
    Sequence:
      call 1 → real message
      call 2 → CancelledError

    Assert: process_one called once with (redis_client, msg_id, fields).
    """
    msg_id = b"1-0"
    fields = {
        "document_version_id": "00000000-0000-0000-0000-000000000001",
        "tenant_id": "00000000-0000-0000-0000-000000000002",
        "bot_id": "00000000-0000-0000-0000-000000000003",
        "attempt": "1",
    }
    results = [(b"ingestion", [(msg_id, fields)])]
    side_effects = [results, asyncio.CancelledError()]
    mock_r = _make_redis_mock(side_effects)

    with (
        patch("app.worker.ingestion.get_redis", return_value=mock_r),
        patch("app.worker.ingestion.ensure_consumer_group", new_callable=AsyncMock),
        patch("app.worker.ingestion.process_one", new_callable=AsyncMock) as mock_process,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_worker()

    mock_process.assert_awaited_once_with(mock_r, msg_id, fields)


# ---------------------------------------------------------------------------
# Test: CancelledError propagates — not swallowed by retry handler
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancelled_error_propagates():
    """
    xreadgroup raises CancelledError directly.  run_worker must NOT catch it
    and must NOT call asyncio.sleep with a backoff value.
    """
    mock_r = _make_redis_mock([asyncio.CancelledError()])

    with (
        patch("app.worker.ingestion.get_redis", return_value=mock_r),
        patch("app.worker.ingestion.ensure_consumer_group", new_callable=AsyncMock),
        patch("app.worker.ingestion.process_one", new_callable=AsyncMock),
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_worker()

    # sleep must NOT have been called (it only fires in the error-backoff path)
    mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# Test: Multiple consecutive TimeoutErrors → backoff doubles up to _BACKOFF_MAX
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_backoff_doubles_up_to_max():
    """
    4 consecutive TimeoutErrors → backoff sleeps: 1, 2, 4, 8 s.
    (Max is 30 s; 8 < 30, so doubling is still visible.)
    """
    n_errors = 4
    side_effects: list = [redis_exc.TimeoutError("t") for _ in range(n_errors)]
    side_effects.append(asyncio.CancelledError())
    mock_r = _make_redis_mock(side_effects)

    sleep_calls: list[float] = []

    async def _fake_sleep(secs):
        sleep_calls.append(secs)

    with (
        patch("app.worker.ingestion.get_redis", return_value=mock_r),
        patch("app.worker.ingestion.ensure_consumer_group", new_callable=AsyncMock),
        patch("app.worker.ingestion.process_one", new_callable=AsyncMock),
        patch("asyncio.sleep", side_effect=_fake_sleep),
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_worker()

    # Expect exponential doubling: 1, 2, 4, 8
    assert sleep_calls == [1.0, 2.0, 4.0, 8.0], f"Got: {sleep_calls}"


# ---------------------------------------------------------------------------
# Test: Pending message reclaim (XAUTOCLAIM) dispatches abandoned messages
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reclaim_pending_messages_dispatches():
    """
    Simulate xautoclaim returning an abandoned message.
    _reclaim_pending_messages must process it via process_one.
    """
    from app.worker.ingestion import _reclaim_pending_messages

    r = MagicMock()
    reclaimed_msg_id = b"2-0"
    reclaimed_fields = {
        b"document_version_id": b"00000000-0000-0000-0000-000000000001",
        b"tenant_id": b"00000000-0000-0000-0000-000000000002",
        b"bot_id": b"00000000-0000-0000-0000-000000000003",
        b"attempt": b"1",
    }
    # First call returns 1 message and end id "0-0"; loop finishes
    r.xautoclaim = AsyncMock(return_value=("0-0", [(reclaimed_msg_id, reclaimed_fields)], []))

    with patch("app.worker.ingestion.process_one", new_callable=AsyncMock) as mock_process:
        await _reclaim_pending_messages(r)

    mock_process.assert_awaited_once()
    args = mock_process.await_args[0]
    assert args[0] == r
    assert args[1] == "2-0"
    assert args[2]["document_version_id"] == "00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Test: Terminal failure records AuditLog entry
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_apply_terminal_failure_writes_audit_log():
    from uuid import uuid4
    from app.models import AuditLog
    from app.worker.ingestion import _apply_terminal_failure

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.add = MagicMock()
    mock_doc = MagicMock()
    mock_ver = MagicMock()

    # scalar_one return values for ver then doc
    mock_session.execute.side_effect = [
        MagicMock(scalar_one=MagicMock(return_value=mock_ver)),
        MagicMock(scalar_one=MagicMock(return_value=mock_doc)),
    ]

    tenant_id = uuid4()
    bot_id = uuid4()
    doc_id = uuid4()
    ver_id = uuid4()

    class FakeSessionContext:
        async def __aenter__(self):
            return mock_session
        async def __aexit__(self, *args):
            pass

    with patch("app.worker.ingestion.tenant_session", return_value=FakeSessionContext()):
        await _apply_terminal_failure(
            tenant_id=tenant_id,
            bot_id=bot_id,
            document_id=doc_id,
            version_id=ver_id,
            error="Test error",
        )

    # Check AuditLog was added to session
    added_objects = [call[0][0] for call in mock_session.add.call_args_list]
    audit_logs = [obj for obj in added_objects if isinstance(obj, AuditLog)]
    assert len(audit_logs) == 1
    audit = audit_logs[0]
    assert audit.action == "document.ingestion_failed"
    assert audit.tenant_id == tenant_id
    assert audit.details["document_id"] == str(doc_id)
    assert audit.details["version_id"] == str(ver_id)
    assert audit.details["bot_id"] == str(bot_id)
    assert audit.details["error"] == "Test error"
