"""
Redis Streams queue helpers for the ingestion worker.

Stream layout
-------------
  ingestion       — primary work stream
  ingestion_dlq   — dead-letter stream (messages that exhausted all retries)

Consumer group
--------------
  Group name: ingestion-workers
  Created idempotently at worker startup via XGROUP CREATE … MKSTREAM.

Message fields (all string-encoded)
------------------------------------
  document_version_id  — UUID of the DocumentVersion to ingest
  tenant_id            — UUID; used to open the correct tenant_session()
  bot_id               — UUID; written to chunks and used for retrieval scoping
  attempt              — "1", "2", or "3"; incremented by the worker before
                         re-queuing; never mutated on the original message

Retry delays (exponential backoff, exclusive to the worker side)
----------------------------------------------------------------
  attempt 1 → failure → sleep 1s  → XADD attempt=2
  attempt 2 → failure → sleep 4s  → XADD attempt=3
  attempt 3 → failure → XADD ingestion_dlq, then XACK — no more retries

See app/worker/ingestion.py for the full processing + status-transition logic.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

STREAM_KEY = "ingestion"
DLQ_KEY = "ingestion_dlq"
GROUP_NAME = "ingestion-workers"
CONSUMER_NAME = "worker-1"  # single-process for now; extend to worker-N for scale-out
MAX_ATTEMPTS = 3
RETRY_DELAYS = {1: 1, 2: 4}  # seconds to sleep after attempt N fails; attempt 3 goes to DLQ

# Redis connection pool — created once per process, shared across all coroutines.
_pool: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """
    Return (or lazily create) the shared async Redis client.

    socket_timeout is set to (WORKER_BLOCK_MS / 1000) + 10 s so that the
    TCP socket never times out while XREADGROUP is legitimately blocking.
    socket_connect_timeout gives the initial handshake a 10 s window.
    """
    global _pool
    if _pool is None:
        block_s = settings.WORKER_BLOCK_MS / 1000.0
        _pool = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=block_s + 10.0,
            socket_connect_timeout=10.0,
        )
    return _pool


async def ensure_consumer_group() -> None:
    """
    Idempotently create the consumer group on the ingestion stream.
    MKSTREAM ensures the stream itself is created if it doesn't exist yet.
    '0' means the group starts reading from the very beginning of the stream
    (important if the stream already has messages from a crashed earlier run).
    """
    r = get_redis()
    try:
        await r.xgroup_create(STREAM_KEY, GROUP_NAME, id="0", mkstream=True)
        logger.info("Consumer group '%s' created on stream '%s'", GROUP_NAME, STREAM_KEY)
    except aioredis.ResponseError as exc:
        if "BUSYGROUP" in str(exc):
            # Group already exists — idempotent, not an error.
            logger.debug("Consumer group '%s' already exists", GROUP_NAME)
        else:
            raise


async def enqueue(
    r: aioredis.Redis,
    *,
    document_version_id: UUID,
    tenant_id: UUID,
    bot_id: UUID,
    attempt: int = 1,
) -> str:
    """
    Add a message to the ingestion stream.  Returns the Redis message ID.
    All field values are string-encoded so the worker can safely decode them
    without knowing Redis's type system.
    """
    msg_id = await r.xadd(
        STREAM_KEY,
        {
            "document_version_id": str(document_version_id),
            "tenant_id": str(tenant_id),
            "bot_id": str(bot_id),
            "attempt": str(attempt),
        },
    )
    logger.info(
        "Enqueued document_version_id=%s attempt=%d msg_id=%s",
        document_version_id,
        attempt,
        msg_id,
    )
    return msg_id


async def enqueue_dlq(
    r: aioredis.Redis,
    *,
    original_fields: dict[str, Any],
    error: str,
) -> None:
    """Write the final-failure record to the dead-letter stream."""
    await r.xadd(
        DLQ_KEY,
        {**original_fields, "error": error},
    )
    logger.error(
        "Moved document_version_id=%s to DLQ after %s attempts: %s",
        original_fields.get("document_version_id"),
        original_fields.get("attempt"),
        error,
    )
