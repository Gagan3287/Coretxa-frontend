"""
Queue inspection script for Redis stream and dead-letter queue (DLQ).

Usage:
    python scripts/inspect_queue.py [--limit 10]
"""
import argparse
import asyncio
import sys

from app.worker.queue import DLQ_KEY, GROUP_NAME, STREAM_KEY, get_redis


async def inspect_queue(limit: int = 10) -> int:
    r = get_redis()
    print("=" * 60)
    print("REDIS QUEUE INSPECTION")
    print("=" * 60)

    # 1. Primary stream inspection
    try:
        stream_len = await r.xlen(STREAM_KEY)
        print(f"[*] Stream '{STREAM_KEY}': {stream_len} total entries")

        # Groups
        try:
            groups = await r.xinfo_groups(STREAM_KEY)
            print(f"[*] Consumer Groups on '{STREAM_KEY}': {len(groups)}")
            for g in groups:
                print(f"    - Group: {g.get('name')}, Consumers: {g.get('consumers')}, Pending: {g.get('pending')}")
        except Exception as e:
            print(f"    (No consumer group info: {e})")

        # Pending summary
        try:
            pending = await r.xpending(STREAM_KEY, GROUP_NAME)
            print(f"[*] Pending summary for group '{GROUP_NAME}': {pending}")
        except Exception:
            pass

    except Exception as exc:
        print(f"[!] Could not inspect primary stream: {exc}")

    print("-" * 60)

    # 2. DLQ inspection
    try:
        dlq_len = await r.xlen(DLQ_KEY)
        print(f"[*] DLQ Stream '{DLQ_KEY}': {dlq_len} total entries")

        if dlq_len > 0:
            entries = await r.xrevrange(DLQ_KEY, count=limit)
            print(f"[*] Latest {len(entries)} DLQ entries:")
            for msg_id, fields in entries:
                print(f"    ID: {msg_id}")
                for k, v in fields.items():
                    print(f"       {k}: {v}")
    except Exception as exc:
        print(f"[!] Could not inspect DLQ: {exc}")

    print("=" * 60)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect Redis Stream and DLQ")
    parser.add_argument("--limit", type=int, default=10, help="Number of DLQ entries to display")
    args = parser.parse_args()

    sys.exit(asyncio.run(inspect_queue(args.limit)))
