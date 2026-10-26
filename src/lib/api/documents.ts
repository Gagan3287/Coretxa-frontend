import type { DocumentItem } from "@/types/document";

// MOCK DATA: replace with real API calls once the backend endpoints are connected.
export const MAX_FILE_BYTES = 10 * 1024 * 1024;

const hoursAgo = (h: number) => new Date(Date.now() - h * 3600_000).toISOString();

let docs: DocumentItem[] = [
  { id: "d1", name: "Refund-policy.pdf", sizeBytes: 482_000, botId: "b1", botName: "Customer Support", status: "ready", progress: 100, uploadedAt: hoursAgo(5) },
  { id: "d2", name: "Employee-handbook-2026.pdf", sizeBytes: 3_200_000, botId: "b2", botName: "HR Policy", status: "ready", progress: 100, uploadedAt: hoursAgo(30) },
  { id: "d3", name: "API-reference.pdf", sizeBytes: 1_450_000, botId: "b3", botName: "Product Docs", status: "processing", progress: 100, uploadedAt: hoursAgo(1) },
  { id: "d4", name: "Scanned-contract.pdf", sizeBytes: 5_100_000, botId: "b1", botName: "Customer Support", status: "failed", progress: 100, uploadedAt: hoursAgo(48), error: "Could not extract text. The PDF may be scanned or password-protected." },
];

const listeners = new Set<(items: DocumentItem[]) => void>();
const delay = (ms = 600) => new Promise((resolve) => setTimeout(resolve, ms));

function notify() {
  const snapshot = [...docs];
  listeners.forEach((fn) => fn(snapshot));
}

function patch(id: string, changes: Partial<DocumentItem>) {
  docs = docs.map((d) => (d.id === id ? { ...d, ...changes } : d));
  notify();
}

export function validateFile(file: File): string | null {
  const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  if (!isPdf) return `${file.name}: only PDF files are supported.`;
  if (file.size === 0) return `${file.name}: the file is empty.`;
  if (file.size > MAX_FILE_BYTES) return `${file.name}: file is larger than 10 MB.`;
  return null;
}

export async function listDocuments(): Promise<DocumentItem[]> {
  await delay();
  return [...docs];
}

export function subscribeDocuments(fn: (items: DocumentItem[]) => void) {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

export function uploadDocument(file: File, bot: { id: string; name: string }) {
  const doc: DocumentItem = {
    id: `d${Date.now()}${Math.floor(Math.random() * 1000)}`,
    name: file.name,
    sizeBytes: file.size,
    botId: bot.id,
    botName: bot.name,
    status: "uploading",
    progress: 0,
    uploadedAt: new Date().toISOString(),
  };
  docs = [doc, ...docs];
  notify();

  let progress = 0;
  const timer = setInterval(() => {
    progress = Math.min(100, progress + 8 + Math.random() * 12);
    if (progress >= 100) {
      clearInterval(timer);
      patch(doc.id, { progress: 100, status: "processing" });
      setTimeout(() => patch(doc.id, { status: "ready" }), 2500);
    } else {
      patch(doc.id, { progress: Math.round(progress) });
    }
  }, 150);

  return doc;
}

export async function deleteDocument(id: string) {
  await delay(400);
  docs = docs.filter((d) => d.id !== id);
  notify();
}