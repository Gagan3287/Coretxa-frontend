import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, tenants
from app.api.v1 import bots, documents
from app.core.config import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cortexa Backend API",
    description="Multi-tenant knowledge base, document ingestion, embeddings, and bot management API engine for Cortexa.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication and tenant management routes (available at /auth and /api/auth)
app.include_router(auth.router)
app.include_router(tenants.router)
app.include_router(auth.router, prefix="/api")
app.include_router(tenants.router, prefix="/api")

# v1 versioned API routes
app.include_router(bots.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "cortexa-backend", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Background ingestion worker — runs inside the same process as the API server.
# This avoids needing a separate Render worker service on the free plan.
# ---------------------------------------------------------------------------

_worker_task: asyncio.Task | None = None


@app.on_event("startup")
async def start_ingestion_worker() -> None:
    """
    Launch the Redis-stream ingestion worker as a background asyncio task.
    It runs alongside uvicorn in the same event loop — no extra Render service needed.
    If the worker crashes (e.g. Redis unreachable on cold start), it restarts
    after a short delay so transient connection errors don't kill the whole process.
    """
    global _worker_task

    async def _resilient_worker() -> None:
        from app.worker.ingestion import run_worker  # local import to avoid circular deps

        backoff = 2.0
        while True:
            try:
                logger.info("Starting ingestion worker background task...")
                await run_worker()
            except asyncio.CancelledError:
                logger.info("Ingestion worker cancelled — shutting down cleanly.")
                return
            except Exception as exc:
                logger.error(
                    "Ingestion worker crashed: %s. Restarting in %.0fs...",
                    exc,
                    backoff,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)  # cap at 60s

    _worker_task = asyncio.create_task(_resilient_worker(), name="ingestion-worker")
    logger.info("Ingestion worker background task created.")


@app.on_event("shutdown")
async def stop_ingestion_worker() -> None:
    """Cancel the worker task cleanly on SIGTERM / server shutdown."""
    global _worker_task
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
    logger.info("Ingestion worker stopped.")
