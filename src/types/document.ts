export type DocumentStatus = "uploading" | "processing" | "ready" | "failed";

export interface DocumentItem {
  id: string;
  name: string;
  sizeBytes: number;
  botId: string;
  botName: string;
  status: DocumentStatus;
  progress: number;
  uploadedAt: string;
  error?: string;
}