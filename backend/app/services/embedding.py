"""
Embedding service — wraps Google GenAI SDK (Gemini embeddings).

embed_texts() accepts an optional api_key override so that per-bot
llm_overrides.embedding_api_key can be used when set; otherwise it falls
back to settings.GOOGLE_API_KEY (the platform default).

The model is chosen only by settings.EMBEDDING_MODEL (e.g. gemini-embedding-001
or gemini-embedding-2-preview).

Task type:
  - RETRIEVAL_DOCUMENT for indexing chunks
  - RETRIEVAL_QUERY for search queries (Phase 3)
Note:
  Both gemini-embedding-001 and gemini-embedding-2-preview accept and respect
  these task types. If task_type turns out to have no effect on a model,
  it still executes normally and does not fail.
"""
import asyncio
import logging
import time
from typing import Sequence

from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Explicit timeout in seconds for Gemini API requests
DEFAULT_EMBEDDING_TIMEOUT: float = 30.0


def _estimate_tokens(texts: Sequence[str]) -> int:
    """Conservative token count estimate: char count / 3 (minimum 1 per non-empty string)."""
    return sum(max(1, len(t) // 3) for t in texts)


def _sanitize_error(exc: Exception, key: str | None) -> str:
    msg = str(exc)
    if key and key in msg:
        msg = msg.replace(key, "[REDACTED]")
    return msg


def _is_quota_exhausted_error(exc: Exception) -> bool:
    err_str = str(exc)
    code = getattr(exc, "code", None)
    return (
        code == 429
        or "429" in err_str
        or "RESOURCE_EXHAUSTED" in err_str
        or "ResourceExhausted" in type(exc).__name__
    )


class _RateLimiter:
    """Token-bucket rate limiter enforcing max RPM and TPM per API key."""

    def __init__(self, max_rpm: int, max_tpm: int):
        self.max_rpm = max_rpm
        self.max_tpm = max_tpm
        self.rpm_tokens = float(max_rpm)
        self.tpm_tokens = float(max_tpm)
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self, estimated_tokens: int) -> None:
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now

            # Refill buckets
            self.rpm_tokens = min(float(self.max_rpm), self.rpm_tokens + elapsed * (self.max_rpm / 60.0))
            self.tpm_tokens = min(float(self.max_tpm), self.tpm_tokens + elapsed * (self.max_tpm / 60.0))

            needed_rpm_wait = (1.0 - self.rpm_tokens) / (self.max_rpm / 60.0) if self.rpm_tokens < 1.0 else 0.0
            tokens_to_wait = min(float(estimated_tokens), float(self.max_tpm))
            needed_tpm_wait = (tokens_to_wait - self.tpm_tokens) / (self.max_tpm / 60.0) if self.tpm_tokens < tokens_to_wait else 0.0

            wait_time = max(needed_rpm_wait, needed_tpm_wait)
            if wait_time > 0:
                logger.info("Throttling embedding request: sleeping %.2fs for rate limits", wait_time)
                await asyncio.sleep(wait_time)
                now = time.monotonic()
                elapsed = now - self.last_update
                self.last_update = now
                self.rpm_tokens = min(float(self.max_rpm), self.rpm_tokens + elapsed * (self.max_rpm / 60.0))
                self.tpm_tokens = min(float(self.max_tpm), self.tpm_tokens + elapsed * (self.max_tpm / 60.0))

            self.rpm_tokens = max(0.0, self.rpm_tokens - 1.0)
            self.tpm_tokens = max(0.0, self.tpm_tokens - float(estimated_tokens))


_RATE_LIMITERS: dict[str, _RateLimiter] = {}


def _get_rate_limiter(api_key: str) -> _RateLimiter:
    if api_key not in _RATE_LIMITERS:
        _RATE_LIMITERS[api_key] = _RateLimiter(settings.EMBED_MAX_RPM, settings.EMBED_MAX_TPM)
    return _RATE_LIMITERS[api_key]


def _parse_embeddings(result: types.EmbedContentResponse | dict) -> list[list[float]]:
    raw_embeddings = getattr(result, "embeddings", None)
    if raw_embeddings is None and isinstance(result, dict):
        raw_embeddings = result.get("embeddings") or result.get("embedding")

    if not raw_embeddings:
        return []
    elif isinstance(raw_embeddings, list) and raw_embeddings and isinstance(raw_embeddings[0], (int, float)):
        return [list(raw_embeddings)]
    else:
        embeddings: list[list[float]] = []
        for item in raw_embeddings:
            if isinstance(item, dict):
                if "values" in item:
                    embeddings.append(list(item["values"]))
                else:
                    embeddings.append(list(item))
            elif hasattr(item, "values") and not callable(item.values) and item.values is not None:
                embeddings.append(list(item.values))
            elif isinstance(item, (list, tuple)):
                embeddings.append(list(item))
            else:
                embeddings.append(list(item))
        return embeddings


async def _embed_batch(
    client: genai.Client,
    model: str,
    batch: list[str],
    task_type: str,
    http_opts: types.HttpOptions | None,
    api_key: str,
) -> list[list[float]]:
    rate_limiter = _get_rate_limiter(api_key)
    estimated_tokens = _estimate_tokens(batch)

    total_waited = 0.0
    backoff = 5.0

    while True:
        await rate_limiter.acquire(estimated_tokens)
        try:
            result = await client.aio.models.embed_content(
                model=model,
                contents=batch,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=settings.EMBEDDING_DIM,
                    http_options=http_opts,
                ),
            )
            return _parse_embeddings(result)
        except Exception as exc:
            if _is_quota_exhausted_error(exc):
                sanitized = _sanitize_error(exc, api_key)
                if total_waited + backoff > settings.EMBED_MAX_WAIT_SECONDS:
                    logger.error(
                        "Embedding quota retry exceeded max wait (%ds): %s",
                        settings.EMBED_MAX_WAIT_SECONDS,
                        sanitized,
                    )
                    raise RuntimeError(f"Embedding request failed: {sanitized}") from None

                logger.warning(
                    "Embedding quota exhausted (429 RESOURCE_EXHAUSTED). Throttling: sleeping %.1fs (total waited: %.1fs / max: %ds)...",
                    backoff,
                    total_waited,
                    settings.EMBED_MAX_WAIT_SECONDS,
                )
                await asyncio.sleep(backoff)
                total_waited += backoff
                backoff = min(backoff * 2, 60.0)
                continue

            sanitized = _sanitize_error(exc, api_key)
            logger.error("Embedding generation failed: %s", sanitized)
            if api_key and api_key in str(exc):
                raise RuntimeError(f"Embedding request failed: {sanitized}") from None
            raise


async def embed_texts(
    texts: Sequence[str],
    *,
    api_key: str | None = None,
    task_type: str = "RETRIEVAL_DOCUMENT",
    model: str | None = None,
    timeout: float = DEFAULT_EMBEDDING_TIMEOUT,
) -> list[list[float]]:
    """
    Embed a batch of texts and return a list of float vectors.
    Batches texts into settings.EMBED_BATCH_SIZE chunks, applies rate limiting
    (RPM/TPM) and retries on 429 quota exhaustion.

    Args:
        texts: One or more strings to embed.
        api_key: Optional API key override (e.g. from bot.llm_overrides).
                 If None or empty, falls back to settings.GOOGLE_API_KEY.
                 Never logged.
        task_type: Embedding task type. Defaults to 'RETRIEVAL_DOCUMENT' for indexing chunks.
                   Use 'RETRIEVAL_QUERY' for user queries.
        model: Optional model override. Defaults to settings.EMBEDDING_MODEL.
        timeout: Explicit request timeout in seconds.

    Returns:
        List of float vectors, one per input text, matching settings.EMBEDDING_DIM (768).

    Raises:
        ValueError: If texts is empty, API key is missing, or returned vector dimension != settings.EMBEDDING_DIM.
        APIError / RuntimeError: On underlying API failures.
    """
    if not texts:
        raise ValueError("embed_texts requires at least one text")

    effective_key = api_key or settings.GOOGLE_API_KEY
    if not effective_key:
        raise ValueError("GOOGLE_API_KEY is not configured")

    effective_model = model or settings.EMBEDDING_MODEL

    timeout_ms = int(timeout * 1000) if timeout is not None else None
    http_opts = types.HttpOptions(timeout=timeout_ms) if timeout_ms is not None else None

    client = genai.Client(api_key=effective_key)

    batch_size = max(1, settings.EMBED_BATCH_SIZE)
    batches = [list(texts[i : i + batch_size]) for i in range(0, len(texts), batch_size)]

    all_embeddings: list[list[float]] = []
    for batch in batches:
        embeddings = await _embed_batch(
            client=client,
            model=effective_model,
            batch=batch,
            task_type=task_type,
            http_opts=http_opts,
            api_key=effective_key,
        )
        all_embeddings.extend(embeddings)

    expected_dim = settings.EMBEDDING_DIM
    for idx, vec in enumerate(all_embeddings):
        if len(vec) != expected_dim:
            raise ValueError(
                f"Embedding vector dimension mismatch at index {idx}: expected {expected_dim}, got {len(vec)}"
            )

    return all_embeddings


async def embed_query(
    text: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    timeout: float = DEFAULT_EMBEDDING_TIMEOUT,
) -> list[float]:
    """
    Embed a single query text for Phase 3 retrieval using RETRIEVAL_QUERY.
    """
    if not text or not text.strip():
        raise ValueError("embed_query requires non-empty query text")

    vectors = await embed_texts(
        [text],
        api_key=api_key,
        task_type="RETRIEVAL_QUERY",
        model=model,
        timeout=timeout,
    )
    return vectors[0]

