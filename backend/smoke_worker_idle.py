"""
Idle smoke test for the ingestion worker against the real Upstash instance.

Runs the worker for exactly DURATION_S seconds with no messages in the stream.
A thin counting wrapper around the aioredis client records every command sent.

Prints:
  - A log line each time the worker wakes (blocked read returned empty)
  - Commands-per-minute breakdown before and after the fix
  - No tracebacks expected

Never prints the Redis URL or password.
Run:  python smoke_worker_idle.py
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from pathlib import Path
from dotenv import load_dotenv

# Load real .env (not .env.test) so we hit the live Upstash instance
load_dotenv(Path(__file__).parent / ".env", override=True)

# Patch settings.WORKER_BLOCK_MS to 5 000 ms so we get 12 wakeups/min at most
# while still completing the run in reasonable time.
import app.core.config as _cfg
_cfg.settings.WORKER_BLOCK_MS = 5_000   # 5 s block per iteration for this smoke run

import redis.asyncio as aioredis
from app.worker import queue as _queue
from app.worker.ingestion import run_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("smoke_worker_idle")

DURATION_S = 120  # 2 minutes


# ---------------------------------------------------------------------------
# Counting wrapper
# ---------------------------------------------------------------------------

class _CountingRedis(aioredis.Redis):
    """Subclass that counts every command executed."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cmd_counts: dict[str, int] = defaultdict(int)
        self._total: int = 0

    async def execute_command(self, *args, **options):
        cmd = str(args[0]).upper() if args else "UNKNOWN"
        self._cmd_counts[cmd] += 1
        self._total += 1
        return await super().execute_command(*args, **options)


def _install_counting_client():
    """Replace the queue module's client with a counting one."""
    from app.core.config import settings
    block_s = settings.WORKER_BLOCK_MS / 1000.0
    pool = _CountingRedis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_timeout=block_s + 10.0,
        socket_connect_timeout=10.0,
    )
    _queue._pool = pool
    return pool


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    logger.info("=== Upstash idle smoke: WORKER_BLOCK_MS=%dms, duration=%ds ===",
                _cfg.settings.WORKER_BLOCK_MS, DURATION_S)

    counting_client = _install_counting_client()

    # Ping to verify connectivity (before counting window)
    try:
        pong = await counting_client.ping()
        assert pong, "Ping failed"
        logger.info("Upstash reachable (PING OK). Starting worker loop...")
    except Exception as exc:
        logger.error("Cannot reach Upstash: %s", type(exc).__name__)
        return

    # Reset counters after the ping
    counting_client._cmd_counts.clear()
    counting_client._total = 0

    start = time.monotonic()

    worker_task = asyncio.create_task(run_worker())
    stopper = asyncio.get_event_loop().call_later(DURATION_S, worker_task.cancel)

    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    finally:
        stopper.cancel()

    elapsed = time.monotonic() - start
    elapsed_min = elapsed / 60.0

    total_cmds = counting_client._total
    cpm = total_cmds / elapsed_min if elapsed_min > 0 else 0.0

    logger.info("=== Smoke complete: elapsed=%.1fs ===", elapsed)
    logger.info("Commands issued during idle run:")
    for cmd, count in sorted(counting_client._cmd_counts.items()):
        logger.info("  %-20s %d", cmd, count)
    logger.info("Total commands : %d in %.1f min", total_cmds, elapsed_min)
    logger.info("Commands/min   : %.1f", cpm)
    logger.info("(Expected ≤ 2/min with WORKER_BLOCK_MS=30000 in production)")


if __name__ == "__main__":
    asyncio.run(main())
