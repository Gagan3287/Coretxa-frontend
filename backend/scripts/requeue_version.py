"""
Re-queue a failed document version for ingestion retry (WP-E3).

Usage:
    python scripts/requeue_version.py --version-id <UUID> [--tenant-id <UUID>] [--bot-id <UUID>]
"""
import argparse
import asyncio
import sys
from uuid import UUID

from sqlalchemy import select

from app.core.database import platform_session, tenant_session
from app.models import Document, DocumentVersion
from app.worker.queue import enqueue, get_redis


async def requeue_version(version_id: UUID, tenant_id: UUID | None = None, bot_id: UUID | None = None) -> int:
    r = get_redis()

    # If tenant_id not supplied, look it up via platform session
    if tenant_id is None or bot_id is None:
        async with platform_session() as session:
            stmt = select(DocumentVersion).where(DocumentVersion.id == version_id)
            res = await session.execute(stmt)
            ver = res.scalar_one_or_none()
            if ver is None:
                print(f"[ERROR] DocumentVersion {version_id} not found in database.")
                return 1
            tenant_id = ver.tenant_id
            bot_id = ver.bot_id
            doc_id = ver.document_id

    # Reset DB status under tenant session
    async with tenant_session(tenant_id) as session:
        v_res = await session.execute(select(DocumentVersion).where(DocumentVersion.id == version_id))
        ver = v_res.scalar_one_or_none()
        if ver:
            ver.status = "pending"
            ver.error_message = None

        d_res = await session.execute(select(Document).where(Document.id == ver.document_id))
        doc = d_res.scalar_one_or_none()
        if doc:
            doc.status = "pending"
            doc.error_message = None

    # Enqueue to Redis stream
    msg_id = await enqueue(
        r,
        document_version_id=version_id,
        tenant_id=tenant_id,
        bot_id=bot_id,
        attempt=1,
    )
    print(f"[SUCCESS] Re-queued version {version_id} (tenant={tenant_id}, bot={bot_id}) as msg_id={msg_id}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-queue a document version for ingestion")
    parser.add_argument("--version-id", required=True, type=UUID, help="DocumentVersion UUID to re-queue")
    parser.add_argument("--tenant-id", type=UUID, default=None, help="Tenant UUID (optional)")
    parser.add_argument("--bot-id", type=UUID, default=None, help="Bot UUID (optional)")
    args = parser.parse_args()

    sys.exit(asyncio.run(requeue_version(args.version_id, args.tenant_id, args.bot_id)))
