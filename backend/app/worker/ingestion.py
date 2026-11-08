"""
Ingestion worker — consumes from the 'ingestion' Redis stream and
processes DocumentVersion rows through chunking + embedding.

Status-transition contract
--------------------------
This section is the authoritative specification; Document.error_message's
docstring in app/models/document.py cross-references it.

SUCCESS PATH  (ingestion completed without exception)
  1.  Insert new Chunk rows (content + embedding) for this version.
  2.  Set  DocumentVersion.status        = "ready"
  3.  Set  Document.status               = "ready"
  4.  Set  Document.current_version_id   = this version's id
  5.  Set  Document.error_message        = None          ← CLEAR on success
      Rationale: a previously-failed document that is successfully re-uploaded
      must not keep showing a stale error in list views.
  All writes happen inside a single tenant_session() transaction. Old version chunk rows are retained.

FAILURE PATH  (exception on attempt N, N < MAX_ATTEMPTS)
  1.  Set  DocumentVersion.status = "processing"  (already set; no change needed)
  2.  Sleep RETRY_DELAYS[N] seconds.
  3.  XADD a new message with attempt=N+1 to the ingestion stream.
  4.  XACK the original message (it is now superseded by the re-queued one).
  Note: Document.status and Document.error_message are NOT touched on
  transient failures — the document stays "processing" so the list view
  shows the in-progress state without flicker.

TERMINAL FAILURE  (exception on attempt MAX_ATTEMPTS = 3)
  1.  Set  DocumentVersion.status        = "failed"
  2.  Set  DocumentVersion.error_message = <error string>      ← authoritative
  3.  Set  Document.status               = "failed"
  4.  Set  Document.error_message        = <same error string> ← denormalized copy
      Rationale: list-documents must surface the error without joining versions.
  5.  XADD the original message fields + error to ingestion_dlq stream.
  6.  XACK the original message from the primary stream.
  Steps 1-4 are in one transaction; steps 5-6 happen after commit so DLQ
  write doesn't block or get rolled back on DB commit failure.

Re-upload / version replacement
--------------------------------
A re-upload creates a NEW DocumentVersion row (version_number += 1) and
enqueues it fresh.  The old version row is never mutated — it stays "ready"
(or "failed") so old chunks remain queryable until the new version goes live.

Resilience contract
-------------------
Transient Redis errors (TimeoutError, ConnectionError) inside the main loop
are caught, logged with a short sanitised message (never the URL or password),
and retried after an exponential backoff starting at 1 s, doubling up to 30 s.
The backoff resets to 1 s after any successful XREADGROUP call.

Shutdown: asyncio.CancelledError is allowed to propagate so that
asyncio.run() exits cleanly when the task is cancelled (Ctrl+C / SIGTERM).
The SIGTERM handler cancels the run_worker task; the CancelledError
unwinds from the blocked XREADGROUP in at most one block-period.
"""
from __future__ import annotations

import asyncio
import logging
import re
import signal
import traceback
import uuid
from pathlib import Path
from uuid import UUID

import redis.asyncio as aioredis
import redis.exceptions as redis_exc
from sqlalchemy import delete, select
from sqlalchemy.exc import DBAPIError, DataError, IntegrityError, StatementError

from app.core.config import settings
from app.core.database import tenant_session
from app.models import AuditLog, Bot, Chunk, Document, DocumentVersion
from app.services.parser import ParseError, extract_and_chunk, sanitize_text
from app.worker.queue import (
    DLQ_KEY,
    GROUP_NAME,
    MAX_ATTEMPTS,
    CONSUMER_NAME,
    RETRY_DELAYS,
    STREAM_KEY,
    enqueue,
    enqueue_dlq,
    ensure_consumer_group,
    get_redis,
)


from app.core.storage import StorageKeyError, get_storage


# ---------------------------------------------------------------------------
# Storage key resolver (WP-D)
# ---------------------------------------------------------------------------


def _resolve_storage_path(storage_key: str) -> str:
    """
    Resolve a storage key or legacy file path to an absolute filesystem path
    using the configured storage backend.
    """
    try:
        return get_storage().resolve_path(storage_key)
    except (StorageKeyError, ValueError) as exc:
        raise ParseError(f"Invalid storage key: {exc}") from exc

logger = logging.getLogger(__name__)

# Backoff bounds for transient Redis errors inside the event loop
_BACKOFF_INITIAL: float = 1.0
_BACKOFF_MAX: float = 30.0

# How often pending-message reclaim and health-check may run (seconds)
_PERIODIC_INTERVAL: float = 60.0

# Minimum idle time (ms) before a pending message is considered abandoned and claimed
_MIN_IDLE_TIME_MS: int = 60_000


# ---------------------------------------------------------------------------
# Error classification and hygiene helpers
# ---------------------------------------------------------------------------


def sanitize_error_message(exc: BaseException | str) -> str:
    """
    Sanitize exception strings before logging or persistence:
    - Keep only exception class + first 300 characters of message
    - Redact anything at or after '[parameters:'
    - Redact URLs with credentials
    - Redact key-like strings, secrets, and passwords
    """
    if isinstance(exc, BaseException):
        cls_name = type(exc).__name__
        msg = str(exc)
    else:
        raw = str(exc)
        if ": " in raw:
            cls_name, msg = raw.split(": ", 1)
        else:
            cls_name = ""
            msg = raw

    # 1. Truncate at "[parameters:" (case-insensitive)
    lower_msg = msg.lower()
    param_idx = lower_msg.find("[parameters:")
    if param_idx != -1:
        msg = msg[:param_idx].rstrip()

    # 2. Redact URLs with credentials
    msg = re.sub(r"://[^/\s:@]+:[^/\s:@]+@", "://***:***@", msg)

    # 3. Redact key-like strings and tokens
    msg = re.sub(r"AIza[0-9A-Za-z-_]{35}", "[REDACTED_KEY]", msg)
    msg = re.sub(r"sk-[0-9A-Za-z-_]{20,}", "[REDACTED_KEY]", msg)
    msg = re.sub(r"(?i)\b(api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[^\s'\",]+['\"]?", r"\1=[REDACTED]", msg)

    # 4. Keep first 300 characters of message
    msg = msg[:300].strip()

    if cls_name and msg:
        return f"{cls_name}: {msg}"
    if msg:
        return msg
    return cls_name



def is_deterministic_error(exc: BaseException) -> bool:
    """
    Determine if an error is deterministic (non-retryable):
    - ParseError, ValueError
    - Postgres/asyncpg DataError, CharacterNotInRepertoireError
    - IntegrityError / constraint violations
    - Validation errors
    """
    if isinstance(exc, (ParseError, ValueError)):
        return True

    type_name = type(exc).__name__
    if type_name in (
        "DataError",
        "CharacterNotInRepertoireError",
        "IntegrityError",
        "NotNullViolationError",
        "CheckViolationError",
        "ForeignKeyViolationError",
        "ValidationError",
        "KeyError",
        "TypeError",
    ):
        return True

    if isinstance(exc, (DataError, IntegrityError, StatementError)):
        return True

    orig = getattr(exc, "orig", None)
    if orig is not None:
        orig_name = type(orig).__name__
        if (
            "DataError" in orig_name
            or "CharacterNotInRepertoire" in orig_name
            or "Integrity" in orig_name
            or "CheckViolation" in orig_name
            or "NotNullViolation" in orig_name
        ):
            return True
        orig_str = str(orig)
        if "CharacterNotInRepertoire" in orig_str or "invalid byte sequence" in orig_str:
            return True

    exc_str = str(exc)
    if "CharacterNotInRepertoire" in exc_str or "invalid byte sequence" in exc_str:
        return True

    return False


# ---------------------------------------------------------------------------
# Core ingestion logic — extract, chunk, embed
# ---------------------------------------------------------------------------


async def _extract_text(file_path: str, content_type: str | None) -> str:
    """Extract and sanitize text using parser service."""
    chunks = extract_and_chunk(file_path, content_type)
    return " ".join(c["content"] for c in chunks)


def _split_into_chunks(text: str, max_tokens: int = 400) -> list[dict]:
    """Sentence boundary chunker for backwards compatibility."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks: list[dict] = []
    current_parts: list[str] = []
    current_tokens = 0
    chunk_index = 0

    for sentence in sentences:
        token_estimate = max(1, len(sentence) // 4)
        if current_tokens + token_estimate > max_tokens and current_parts:
            chunks.append(
                {
                    "content": sanitize_text(" ".join(current_parts)),
                    "chunk_index": chunk_index,
                    "section_title": None,
                    "token_count": current_tokens,
                    "page_number": 1,
                }
            )
            chunk_index += 1
            current_parts = []
            current_tokens = 0
        current_parts.append(sentence)
        current_tokens += token_estimate

    if current_parts:
        chunks.append(
            {
                "content": sanitize_text(" ".join(current_parts)),
                "chunk_index": chunk_index,
                "section_title": None,
                "token_count": current_tokens,
                "page_number": 1,
            }
        )

    return chunks



async def _embed_chunks(chunk_texts: list[str], *, api_key: str | None = None) -> list[list[float]]:
    """
    Call the embedding service.  Returns a list of float vectors, one per chunk.
    Raises on API error — the caller (process_one) will treat this as a retryable failure.
    """
    from app.services.embedding import embed_texts  # noqa: PLC0415

    return await embed_texts(chunk_texts, api_key=api_key, task_type="RETRIEVAL_DOCUMENT")


# ---------------------------------------------------------------------------
# Status-transition helpers — the two paths you asked to review
# ---------------------------------------------------------------------------


async def _apply_success(
    *,
    tenant_id: UUID,
    bot_id: UUID,
    document_id: UUID,
    version: DocumentVersion,
    chunk_dicts: list[dict],
    embeddings: list[list[float]],
) -> None:
    """
    SUCCESS PATH — writes inside a single tenant_session transaction.

    Steps (in order):
      1. Load Document (for reference / current_version_id logging).
      2. Insert new Chunk rows for this version.
      3. Set DocumentVersion.status = "ready".
      4. Set Document.status = "ready".
      5. Set Document.current_version_id = version.id.
      6. Set Document.error_message = None.   ← explicit clear-on-success
    """
    async with tenant_session(tenant_id) as session:
        # 1. Load Document first.
        doc_result = await session.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = doc_result.scalar_one()

        if doc.current_version_id is not None and doc.current_version_id != version.id:
            logger.info(
                "Updating document %s to new version %s (previous version was %s)",
                document_id,
                version.id,
                doc.current_version_id,
            )

        # 3. Insert new chunks for this version.
        for chunk_dict, embedding in zip(chunk_dicts, embeddings):
            # Use parser-supplied chunk_metadata if available (v2 chunker),
            # otherwise build basic metadata for backwards compatibility.
            metadata = chunk_dict.get("chunk_metadata") or {}
            if not metadata:
                metadata = {
                    "embedding_model": settings.EMBEDDING_MODEL,
                    "embedding_dim": settings.EMBEDDING_DIM,
                }
                if "page_number" in chunk_dict:
                    metadata["page_number"] = chunk_dict["page_number"]
                    metadata["page_numbers"] = [chunk_dict["page_number"]]
            # Always ensure embedding_model and embedding_dim are present
            metadata.setdefault("embedding_model", settings.EMBEDDING_MODEL)
            metadata.setdefault("embedding_dim", settings.EMBEDDING_DIM)

            chunk = Chunk(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                bot_id=bot_id,
                document_id=document_id,
                document_version_id=version.id,
                content=chunk_dict["content"],
                chunk_index=chunk_dict["chunk_index"],
                section_title=chunk_dict.get("section_title"),
                token_count=chunk_dict.get("token_count"),
                embedding=embedding,
                chunk_metadata=metadata,
            )
            session.add(chunk)

        # 4. Advance the version's own status.
        version_result = await session.execute(
            select(DocumentVersion).where(DocumentVersion.id == version.id)
        )
        ver = version_result.scalar_one()
        ver.status = "ready"

        # 5-7. Update Document atomically.
        doc.status = "ready"
        doc.current_version_id = version.id
        doc.error_message = None  # ← CLEAR: re-upload success must erase prior error

    logger.info(
        "SUCCESS: document_id=%s version_id=%s chunks=%d",
        document_id,
        version.id,
        len(chunk_dicts),
    )


async def _apply_terminal_failure(
    *,
    tenant_id: UUID,
    bot_id: UUID | None = None,
    document_id: UUID,
    version_id: UUID,
    error: str,
) -> None:
    """
    TERMINAL FAILURE PATH — writes inside a single tenant_session transaction.

    Both DocumentVersion and Document are updated together so that if the
    commit fails, neither ends up in an inconsistent "one updated, one not" state.
    Also records an AuditLog entry for the terminal failure.
    All error messages are sanitized before storage.
    """
    sanitized_err = sanitize_error_message(error)
    async with tenant_session(tenant_id) as session:
        # DocumentVersion — authoritative record of what went wrong.
        ver_result = await session.execute(
            select(DocumentVersion).where(DocumentVersion.id == version_id)
        )
        ver = ver_result.scalar_one()
        ver.status = "failed"
        ver.error_message = sanitized_err

        # Document — denormalized copy for fast list-view queries.
        doc_result = await session.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = doc_result.scalar_one()
        doc.status = "failed"
        doc.error_message = sanitized_err

        # Audit log for failed ingestion
        details = {
            "document_id": str(document_id),
            "version_id": str(version_id),
            "error": sanitized_err,
        }
        if bot_id:
            details["bot_id"] = str(bot_id)

        audit = AuditLog(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            actor_id=None,
            action="document.ingestion_failed",
            details=details,
        )
        session.add(audit)

    logger.error(
        "TERMINAL FAILURE: document_id=%s version_id=%s error=%s",
        document_id,
        version_id,
        sanitized_err,
    )


# ---------------------------------------------------------------------------
# Per-message processor
# ---------------------------------------------------------------------------


async def process_one(
    r: aioredis.Redis,
    stream_msg_id: str,
    fields: dict[str, str],
) -> None:
    """
    Process a single ingestion message.  Called by the main event loop.

    Raises nothing — all exceptions are caught here; retry/DLQ logic is
    handled internally so the event loop can safely continue to the next
    message.
    """
    version_id = UUID(fields["document_version_id"])
    tenant_id = UUID(fields["tenant_id"])
    bot_id = UUID(fields["bot_id"])
    attempt = int(fields["attempt"])

    logger.info(
        "Processing document_version_id=%s attempt=%d", version_id, attempt
    )

    try:
        # ---- Load version and bot row ----
        async with tenant_session(tenant_id) as session:
            ver_result = await session.execute(
                select(DocumentVersion).where(DocumentVersion.id == version_id)
            )
            ver = ver_result.scalar_one_or_none()
            if ver is None:
                # Row was deleted (e.g. document cascade-deleted) — nothing to do.
                logger.warning("DocumentVersion %s not found; skipping", version_id)
                await r.xack(STREAM_KEY, GROUP_NAME, stream_msg_id)
                return

            document_id = ver.document_id
            file_path = ver.file_path
            content_type = ver.content_type

            # Check bot llm_overrides for custom embedding API key
            bot_result = await session.execute(
                select(Bot).where(Bot.id == bot_id)
            )
            bot = bot_result.scalar_one_or_none()
            embedding_api_key = None
            if bot and bot.llm_overrides:
                embedding_api_key = bot.llm_overrides.get("embedding_api_key") or bot.llm_overrides.get("gemini_api_key")

            # Mark as processing so the API reflects in-progress state.
            ver.status = "processing"

        # ---- Extract / chunk / embed ----
        # Resolve POSIX storage key to actual filesystem path.
        # Legacy rows may have Windows-style paths — _resolve_storage_path normalizes.
        resolved_path = _resolve_storage_path(file_path)
        chunk_dicts = extract_and_chunk(resolved_path, content_type)
        # B6: embed f"{section_title}\n{content}" but store content clean.
        def _make_embed_text(c: dict) -> str:
            title = c.get("section_title")
            content = c["content"]
            return f"{title}\n{content}" if title else content

        embeddings = await _embed_chunks(
            [_make_embed_text(c) for c in chunk_dicts],
            api_key=embedding_api_key,
        )

        # ---- Apply success with in-process DB write retry ----
        db_max_attempts = 3
        db_backoff = 0.5
        for db_attempt in range(1, db_max_attempts + 1):
            try:
                await _apply_success(
                    tenant_id=tenant_id,
                    bot_id=bot_id,
                    document_id=document_id,
                    version=ver,
                    chunk_dicts=chunk_dicts,
                    embeddings=embeddings,
                )
                break
            except Exception as db_exc:
                if is_deterministic_error(db_exc) or db_attempt == db_max_attempts:
                    raise db_exc
                logger.warning(
                    "Transient DB write failure on attempt %d/%d for version %s: %s. Retrying in-process...",
                    db_attempt,
                    db_max_attempts,
                    version_id,
                    sanitize_error_message(db_exc),
                )
                await asyncio.sleep(db_backoff * (2 ** (db_attempt - 1)))

        # ---- ACK the message only after the DB commit succeeded ----
        await r.xack(STREAM_KEY, GROUP_NAME, stream_msg_id)

    except Exception as exc:  # noqa: BLE001
        sanitized_error = sanitize_error_message(exc)
        logger.warning(
            "Attempt %d failed for version %s: %s",
            attempt,
            version_id,
            sanitized_error,
        )

        deterministic = is_deterministic_error(exc)
        if not deterministic and attempt < MAX_ATTEMPTS:
            # ---- Transient failure: sleep, re-queue, ACK original ----
            delay = RETRY_DELAYS[attempt]
            logger.info("Retrying in %ds (next attempt=%d)", delay, attempt + 1)
            await asyncio.sleep(delay)
            await enqueue(
                r,
                document_version_id=version_id,
                tenant_id=tenant_id,
                bot_id=bot_id,
                attempt=attempt + 1,
            )
            await r.xack(STREAM_KEY, GROUP_NAME, stream_msg_id)

        else:
            # ---- Terminal failure: update DB, write DLQ, ACK original ----
            try:
                await _apply_terminal_failure(
                    tenant_id=tenant_id,
                    bot_id=bot_id,
                    document_id=document_id,  # type: ignore[arg-type]
                    version_id=version_id,
                    error=sanitized_error,
                )
            except Exception as db_exc:
                # DB write failed — still write DLQ so the failure is recorded
                sanitized_db_exc = sanitize_error_message(db_exc)
                logger.critical(
                    "CRITICAL: could not write terminal failure to DB for version %s: %s",
                    version_id,
                    sanitized_db_exc,
                )
                await enqueue_dlq(r, original_fields=fields, error=sanitized_error)
                # No XACK — leave message pending for manual investigation.
                return

            # DB committed → write DLQ → ACK.
            await enqueue_dlq(r, original_fields=fields, error=sanitized_error)
            await r.xack(STREAM_KEY, GROUP_NAME, stream_msg_id)



# ---------------------------------------------------------------------------
# Main worker event loop
# ---------------------------------------------------------------------------

async def _reclaim_pending_messages(r: aioredis.Redis) -> None:
    """
    Reclaim abandoned messages from crashed workers using XAUTOCLAIM.
    Scans the pending entries list (PEL) for messages idle >= _MIN_IDLE_TIME_MS,
    reassigns them to this consumer, and processes them.
    """
    try:
        start_id = "0-0"
        while True:
            claim_result = await r.xautoclaim(
                STREAM_KEY,
                GROUP_NAME,
                CONSUMER_NAME,
                min_idle_time=_MIN_IDLE_TIME_MS,
                start_id=start_id,
                count=10,
            )
            if not isinstance(claim_result, (list, tuple)) or len(claim_result) < 2:
                break

            next_start_id = claim_result[0]
            messages = claim_result[1]

            for msg_id, fields in messages:
                msg_id_str = msg_id.decode("utf-8") if isinstance(msg_id, bytes) else str(msg_id)
                decoded_fields = {}
                for k, v in fields.items():
                    k_str = k.decode("utf-8") if isinstance(k, bytes) else str(k)
                    v_str = v.decode("utf-8") if isinstance(v, bytes) else str(v)
                    decoded_fields[k_str] = v_str

                logger.info("Reclaimed abandoned pending message %s", msg_id_str)
                await process_one(r, msg_id_str, decoded_fields)

            if not messages or next_start_id in ("0-0", b"0-0", 0, None):
                break
            start_id = next_start_id if isinstance(next_start_id, str) else next_start_id.decode("utf-8")
    except Exception as exc:
        logger.warning("Pending message reclaim failed: %s", exc)


async def run_worker() -> None:
    """
    Main loop: XREADGROUP > process_one > loop.

    BLOCK=WORKER_BLOCK_MS keeps the loop responsive while avoiding a tight
    spin when the stream is empty.  socket_timeout is set to
    (WORKER_BLOCK_MS / 1000) + 10 s in get_redis() so the TCP socket never
    expires during a legitimate blocked read.

    Resilience
    ----------
    * redis.exceptions.TimeoutError / ConnectionError inside the read loop are
      caught, logged without the URL or password, and retried with exponential
      backoff (1 s → 2 s → … → 30 s).  Backoff resets after a successful read.
    * asyncio.CancelledError is allowed to propagate so the task exits cleanly
      on Ctrl+C or SIGTERM.

    Shutdown
    --------
    SIGTERM installs a signal handler that cancels the current task.  The
    CancelledError unwinds from the blocked XREADGROUP within one block-period
    (≤ WORKER_BLOCK_MS ms) and the process exits.
    """
    r = get_redis()
    await ensure_consumer_group()
    await _reclaim_pending_messages(r)
    logger.info(
        "Ingestion worker started. Listening on stream '%s' (block=%dms)",
        STREAM_KEY,
        settings.WORKER_BLOCK_MS,
    )

    # ---- SIGTERM → cancel the running task cleanly ----
    loop = asyncio.get_running_loop()
    current_task = asyncio.current_task()

    def _shutdown_handler(signum, frame):  # pragma: no cover
        logger.info("SIGTERM received — shutting down worker")
        if current_task is not None:
            loop.call_soon_threadsafe(current_task.cancel)

    signal.signal(signal.SIGTERM, _shutdown_handler)

    backoff: float = _BACKOFF_INITIAL
    _last_periodic: float = loop.time()

    while True:
        # ---------- periodic maintenance (≤ once per minute) ----------
        now = loop.time()
        if now - _last_periodic >= _PERIODIC_INTERVAL:
            _last_periodic = now
            await _reclaim_pending_messages(r)
            logger.debug("Worker heartbeat (idle periodic tick)")

        # ---------- read from stream ----------
        try:
            results = await r.xreadgroup(
                GROUP_NAME,
                CONSUMER_NAME,
                {STREAM_KEY: ">"},
                count=1,
                block=settings.WORKER_BLOCK_MS,
            )
        except asyncio.CancelledError:
            # Propagate cleanly so asyncio.run() exits gracefully
            logger.info("Worker loop cancelled — exiting")
            raise
        except (redis_exc.TimeoutError, redis_exc.ConnectionError) as exc:
            # Transient Redis error — log sanitised message, back off, retry
            err_type = type(exc).__name__
            logger.warning(
                "Transient Redis error (%s): %s — retrying in %.0fs",
                err_type,
                exc,
                backoff,
            )
            try:
                await asyncio.sleep(backoff)
            except asyncio.CancelledError:
                logger.info("Worker loop cancelled during backoff — exiting")
                raise
            backoff = min(backoff * 2, _BACKOFF_MAX)
            continue

        # Successful read — reset backoff
        backoff = _BACKOFF_INITIAL

        if not results:
            continue  # blocked read timed out; nothing new

        for _stream, messages in results:
            for msg_id, fields in messages:
                await process_one(r, msg_id, fields)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())
