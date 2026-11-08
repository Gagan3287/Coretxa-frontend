"""
Cortexa retrieval service — Phase 3 stub.

This module will implement the RAG retrieval pipeline:
  embed query text → vector search in chunks → assemble context → call LLM router.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TODO (Phase 3) — CRITICAL: filter chunks by document_version_id, NOT document_id
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The retrieval query MUST join through Document.current_version_id and filter:

    WHERE chunks.document_version_id = documents.current_version_id

NOT:

    WHERE chunks.document_id = :document_id   ← WRONG — returns chunks from
                                                  ALL versions of that document,
                                                  including in-progress or failed
                                                  re-uploads.

Why this matters:
  When a tenant re-uploads a document, Phase 2 creates a new DocumentVersion
  with status='pending'/'processing' while the old version stays status='ready'.
  Document.current_version_id still points at the OLD (ready) version until the
  worker successfully commits the new version.

  If retrieval filters only on document_id, it will pick up chunks from BOTH the
  ready old version AND the in-progress/failed new version during the re-upload
  window — producing mixed, inconsistent context for the LLM.

  Filtering on document_version_id = documents.current_version_id ensures only
  the single authoritative, fully-ingested version's chunks are ever retrieved.

Example SQL shape (to be implemented in Phase 3):

    SELECT c.*
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE c.tenant_id = current_setting('app.tenant_id', true)::uuid
      AND c.document_version_id = d.current_version_id
      AND c.embedding <=> :query_embedding < :similarity_threshold
    ORDER BY c.embedding <=> :query_embedding
    LIMIT :top_k;
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
# Phase 3 implementation goes here.
