"""
Unit tests for app.services.embedding.
Uses unittest.mock to mock genai.Client and assert:
  - Client initialized with api_key (or fallback)
  - Model matches settings.EMBEDDING_MODEL (or passed override)
  - output_dimensionality matches settings.EMBEDDING_DIM (768)
  - task_type is RETRIEVAL_DOCUMENT for chunks and RETRIEVAL_QUERY for queries
  - http_options timeout matches 30000 ms (30.0s)
  - Responses with incorrect dimension (e.g., 3072) are rejected with ValueError
"""
from unittest.mock import AsyncMock, patch
import pytest
from google.genai import types

from app.core.config import settings
from app.services.embedding import embed_query, embed_texts


@pytest.mark.asyncio
async def test_embed_texts_request_parameters():
    mock_response = types.EmbedContentResponse(
        embeddings=[
            types.ContentEmbedding(values=[0.1] * 768),
            types.ContentEmbedding(values=[0.2] * 768),
        ]
    )
    with patch("google.genai.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_embed = AsyncMock(return_value=mock_response)
        mock_client.aio.models.embed_content = mock_embed

        vectors = await embed_texts(
            ["chunk one", "chunk two"],
            api_key="custom_bot_key",
        )

        # Assert Client initialized with api_key
        mock_client_cls.assert_called_once_with(api_key="custom_bot_key")

        # Assert embed_content called with correct parameters
        mock_embed.assert_awaited_once()
        kwargs = mock_embed.await_args.kwargs
        assert kwargs["model"] == settings.EMBEDDING_MODEL
        assert kwargs["contents"] == ["chunk one", "chunk two"]
        config = kwargs["config"]
        assert config.output_dimensionality == 768
        assert config.task_type == "RETRIEVAL_DOCUMENT"
        assert config.http_options.timeout == 30000

        assert len(vectors) == 2
        assert len(vectors[0]) == 768
        assert len(vectors[1]) == 768


@pytest.mark.asyncio
async def test_embed_query_request_parameters():
    mock_response = types.EmbedContentResponse(
        embeddings=[
            types.ContentEmbedding(values=[0.3] * 768),
        ]
    )
    with patch("google.genai.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_embed = AsyncMock(return_value=mock_response)
        mock_client.aio.models.embed_content = mock_embed

        vector = await embed_query("What is the company leave policy?")

        mock_embed.assert_awaited_once()
        kwargs = mock_embed.await_args.kwargs
        assert kwargs["model"] == settings.EMBEDDING_MODEL
        assert kwargs["contents"] == ["What is the company leave policy?"]
        config = kwargs["config"]
        assert config.output_dimensionality == 768
        assert config.task_type == "RETRIEVAL_QUERY"
        assert config.http_options.timeout == 30000
        assert len(vector) == 768


@pytest.mark.asyncio
async def test_rejects_3072_length_response():
    # If the API returned default 3072 dimensions, it must be rejected
    mock_response = types.EmbedContentResponse(
        embeddings=[
            types.ContentEmbedding(values=[0.5] * 3072),
        ]
    )
    with patch("google.genai.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.aio.models.embed_content = AsyncMock(return_value=mock_response)

        with pytest.raises(ValueError, match="dimension mismatch.*expected 768, got 3072"):
            await embed_texts(["sample text"])


@pytest.mark.asyncio
async def test_embed_texts_empty_input_rejected():
    with pytest.raises(ValueError, match="embed_texts requires at least one text"):
        await embed_texts([])


@pytest.mark.asyncio
async def test_embed_query_empty_input_rejected():
    with pytest.raises(ValueError, match="embed_query requires non-empty query text"):
        await embed_query("   ")


@pytest.mark.asyncio
async def test_embed_texts_batches_correctly():
    """Verify that input texts larger than EMBED_BATCH_SIZE are sliced into multiple batch calls."""
    texts = [f"chunk {i}" for i in range(35)]  # with batch size 16 -> 3 batches (16, 16, 3)

    def _make_response(batch):
        return types.EmbedContentResponse(
            embeddings=[types.ContentEmbedding(values=[0.1] * 768) for _ in batch]
        )

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_embed = AsyncMock(side_effect=lambda **kwargs: _make_response(kwargs["contents"]))
        mock_client.aio.models.embed_content = mock_embed

        with patch.object(settings, "EMBED_BATCH_SIZE", 16):
            vectors = await embed_texts(texts, api_key="test_key")

        assert len(vectors) == 35
        assert mock_embed.await_count == 3
        calls = mock_embed.await_args_list
        assert len(calls[0].kwargs["contents"]) == 16
        assert len(calls[1].kwargs["contents"]) == 16
        assert len(calls[2].kwargs["contents"]) == 3


@pytest.mark.asyncio
async def test_embed_texts_retries_on_429_quota_exhaustion():
    """Verify that a 429 RESOURCE_EXHAUSTED error triggers exponential backoff and succeeds on retry."""
    mock_success = types.EmbedContentResponse(
        embeddings=[types.ContentEmbedding(values=[0.2] * 768)]
    )
    error_429 = Exception("ClientError: 429 RESOURCE_EXHAUSTED: You exceeded your current quota")

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_embed = AsyncMock(side_effect=[error_429, mock_success])
        mock_client.aio.models.embed_content = mock_embed

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            vectors = await embed_texts(["chunk text"], api_key="secret_google_key")

        assert len(vectors) == 1
        assert mock_embed.await_count == 2
        mock_sleep.assert_awaited_once_with(5.0)


@pytest.mark.asyncio
async def test_embed_texts_429_exceeds_max_wait():
    """Verify that 429 errors exceeding EMBED_MAX_WAIT_SECONDS raise RuntimeError and redact secrets."""
    error_429 = Exception("ClientError: 429 RESOURCE_EXHAUSTED: key secret_google_key exceeded quota")

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_embed = AsyncMock(side_effect=error_429)
        mock_client.aio.models.embed_content = mock_embed

        with patch.object(settings, "EMBED_MAX_WAIT_SECONDS", 10):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(RuntimeError) as exc_info:
                    await embed_texts(["chunk text"], api_key="secret_google_key")

        assert "secret_google_key" not in str(exc_info.value)
        assert "[REDACTED]" in str(exc_info.value)


@pytest.mark.asyncio
async def test_rate_limiter_throttles():
    """Verify token bucket rate limiter throttles and sleeps when capacity is exhausted."""
    from app.services.embedding import _RateLimiter

    limiter = _RateLimiter(max_rpm=1, max_tpm=100)
    # 1 request token available initially
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await limiter.acquire(estimated_tokens=10)
        mock_sleep.assert_not_called()

        # Second request immediate — rpm bucket is 0, requires wait
        await limiter.acquire(estimated_tokens=10)
        mock_sleep.assert_awaited_once()
        wait_arg = mock_sleep.await_args[0][0]
        assert wait_arg > 0
