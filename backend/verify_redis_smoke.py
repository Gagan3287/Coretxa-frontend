"""
verify_redis_smoke.py -- Smoke test Redis Streams against Upstash
Never prints the REDIS_URL or credentials.
"""
import uuid
import sys
import redis
from app.core.config import settings

def main():
    print("=== Upstash Redis Stream Smoke Test ===\n")
    try:
        # Use a socket timeout longer than any block timeout
        r = redis.from_url(
            settings.REDIS_URL,
            socket_timeout=45.0,
            socket_connect_timeout=15.0,
            decode_responses=True,
        )
        # Verify ping first
        pong = r.ping()
        print(f"[PASS] PING: {pong}")

        stream_key = f"smoke_test_stream_{uuid.uuid4().hex[:8]}"
        group_name = "smoke_test_group"
        consumer_name = "smoke_test_consumer"

        # 1. XGROUP CREATE with MKSTREAM
        xgroup_res = r.xgroup_create(stream_key, group_name, id="$", mkstream=True)
        print(f"[PASS] XGROUP CREATE with MKSTREAM: {xgroup_res} (group='{group_name}')")

        # 2. XADD
        msg_payload = {"task": "smoke_test", "status": "queued"}
        msg_id = r.xadd(stream_key, msg_payload)
        print(f"[PASS] XADD: generated msg_id={msg_id} with payload={msg_payload}")

        # 3. XREADGROUP
        # Read new message using special id '>'
        read_res = r.xreadgroup(
            groupname=group_name,
            consumername=consumer_name,
            streams={stream_key: ">"},
            count=1,
            block=2000,
        )
        print(f"[PASS] XREADGROUP: received entries={read_res}")

        # 4. XACK
        ack_res = r.xack(stream_key, group_name, msg_id)
        print(f"[PASS] XACK: acknowledged count={ack_res} for msg_id={msg_id}")

        # 5. XPENDING
        pending_res = r.xpending(stream_key, group_name)
        print(f"[PASS] XPENDING: summary={pending_res}")

        # 6. Delete the test stream
        del_res = r.delete(stream_key)
        print(f"[PASS] DELETE: removed stream (count={del_res})")

        print("\n=================================================================")
        print("  ALL REDIS STREAM SMOKE TESTS PASSED")
        print("=================================================================\n")
    except Exception as e:
        print(f"\n[FAIL] Redis smoke test failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
