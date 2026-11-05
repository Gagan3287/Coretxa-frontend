import { apiClient } from "./client";
import type { DocumentItem, DocumentStatus } from "@/types/document";
import type { Bot } from "@/types/bot";

export const MAX_FILE_BYTES = 10 * 1024 * 1024;

// ---------------------------------------------------------------------------
// Backend response shapes
// ---------------------------------------------------------------------------

interface BackendDocumentDetail {
  document_id: string;
  bot_id: string;
  tenant_id: string;
  original_filename: string;
  status: string;
  current_version_id: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

interface BackendDocumentListResponse {
  documents: BackendDocumentDetail[];
  total: number;
}

interface BackendDocumentUploadResponse {
  document_id: string;
  version_id: string;
  filename: string;
  size_bytes: number;
  status: string;
  queue_position: number | null;
}

// ---------------------------------------------------------------------------
// Client-side helpers
// ---------------------------------------------------------------------------

function mapStatus(s: string): DocumentStatus {
  if (s === "ready") return "ready";
  if (s === "failed") return "failed";
  if (s === "processing") return "processing";
  return "processing"; // pending maps to processing in UI
}

function mapDoc(d: BackendDocumentDetail, botName = ""): DocumentItem {
  return {
    id: d.document_id,
    name: d.original_filename,
    sizeBytes: 0, // not available from list; detail would have it
    botId: d.bot_id,
    botName,
    status: mapStatus(d.status),
    progress: d.status === "ready" || d.status === "failed" ? 100 : 50,
    uploadedAt: d.created_at,
    error: d.error_message ?? undefined,
  };
}

// ---------------------------------------------------------------------------
// Subscription / polling support
// ---------------------------------------------------------------------------

const listeners = new Set<(items: DocumentItem[]) => void>();
let cachedDocs: DocumentItem[] = [];

function notify() {
  const snapshot = [...cachedDocs];
  listeners.forEach((fn) => fn(snapshot));
}

export function subscribeDocuments(fn: (items: DocumentItem[]) => void) {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

export function validateFile(file: File): string | null {
  const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  if (!isPdf) return `${file.name}: only PDF files are supported.`;
  if (file.size === 0) return `${file.name}: the file is empty.`;
  if (file.size > MAX_FILE_BYTES) return `${file.name}: file is larger than 10 MB.`;
  return null;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function listDocuments(bots?: Bot[]): Promise<DocumentItem[]> {
  if (!bots || bots.length === 0) {
    // No bots = no documents
    cachedDocs = [];
    return [];
  }

  try {
    // Fetch documents for all bots in parallel
    const botNameMap = Object.fromEntries(bots.map((b) => [b.id, b.name]));

    const results = await Promise.allSettled(
      bots.map((bot) =>
        apiClient<BackendDocumentListResponse>(`/api/v1/bots/${bot.id}/documents`).then((r) =>
          r.documents.map((d) => mapDoc(d, botNameMap[bot.id] || ""))
        )
      )
    );

    const allDocs: DocumentItem[] = [];
    for (const result of results) {
      if (result.status === "fulfilled") {
        allDocs.push(...result.value);
      }
    }

    // Sort by uploadedAt descending
    allDocs.sort((a, b) => new Date(b.uploadedAt).getTime() - new Date(a.uploadedAt).getTime());
    cachedDocs = allDocs;
    return allDocs;
  } catch {
    throw new Error("Failed to load documents.");
  }
}

export async function uploadDocument(file: File, bot: Bot): Promise<DocumentItem> {
  const formData = new FormData();
  formData.append("file", file);

  const uploadResp = await apiClient<BackendDocumentUploadResponse>(
    `/api/v1/bots/${bot.id}/documents`,
    {
      method: "POST",
      body: formData,
    }
  );

  const doc: DocumentItem = {
    id: uploadResp.document_id,
    name: uploadResp.filename,
    sizeBytes: uploadResp.size_bytes,
    botId: bot.id,
    botName: bot.name,
    status: mapStatus(uploadResp.status),
    progress: 30,
    uploadedAt: new Date().toISOString(),
  };

  cachedDocs = [doc, ...cachedDocs];
  notify();
  return doc;
}

export async function deleteDocument(id: string, botId: string): Promise<void> {
  await apiClient<void>(`/api/v1/bots/${botId}/documents/${id}`, {
    method: "DELETE",
  });
  cachedDocs = cachedDocs.filter((d) => d.id !== id);
  notify();
}

export async function refreshDocumentStatus(botId: string): Promise<BackendDocumentDetail[]> {
  const data = await apiClient<BackendDocumentListResponse>(`/api/v1/bots/${botId}/documents`);
  return data.documents;
}