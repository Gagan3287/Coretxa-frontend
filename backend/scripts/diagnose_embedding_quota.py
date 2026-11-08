"""
Diagnostic script for Gemini Embedding API quota and connectivity.

Usage:
    python scripts/diagnose_embedding_quota.py [--key <optional_api_key>]
"""
import argparse
import asyncio
import sys
import time

from app.core.config import settings
from app.services.embedding import embed_texts


async def run_diagnostics(api_key: str | None = None) -> int:
    target_key = api_key or settings.GOOGLE_API_KEY
    if not target_key:
        print("[ERROR] No Google API key found in --key or settings.GOOGLE_API_KEY.")
        return 1

    masked_key = target_key[:6] + "..." + target_key[-4:] if len(target_key) > 10 else "***"
    print(f"[*] Testing embedding with API key: {masked_key}")
    print(f"[*] Model: {settings.EMBEDDING_MODEL}")
    print(f"[*] Expected dimension: {settings.EMBEDDING_DIM}")
    print(f"[*] Max RPM: {settings.EMBED_MAX_RPM}, Max TPM: {settings.EMBED_MAX_TPM}")

    sample_texts = [
        "Community garden site planning and soil preparation guidelines.",
        "Compost pile carbon to nitrogen ratio balancing techniques.",
    ]

    t0 = time.perf_counter()
    try:
        vectors = await embed_texts(sample_texts, api_key=target_key)
        duration = time.perf_counter() - t0
        print(f"[SUCCESS] Successfully embedded {len(sample_texts)} texts in {duration:.2f}s")
        print(f"[*] Vectors returned: {len(vectors)}, Dimension: {len(vectors[0])}")
        if len(vectors[0]) != settings.EMBEDDING_DIM:
            print(f"[WARNING] Dimension mismatch: expected {settings.EMBEDDING_DIM}, got {len(vectors[0])}")
        return 0
    except Exception as exc:
        duration = time.perf_counter() - t0
        print(f"[FAILURE] Embedding call failed after {duration:.2f}s: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Diagnose Gemini Embedding Quota")
    parser.add_argument("--key", help="Optional API key override", default=None)
    args = parser.parse_args()

    exit_code = asyncio.run(run_diagnostics(args.key))
    sys.exit(exit_code)
