"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { FileText, Trash2, UploadCloud } from "lucide-react";
import Badge from "@/components/ui/badge";
import Button from "@/components/ui/button";
import Dialog from "@/components/ui/dialog";
import EmptyState from "@/components/ui/empty-state";
import PageHeader from "@/components/ui/page-header";
import Select from "@/components/ui/select";
import Skeleton from "@/components/ui/skeleton";
import { listBots } from "@/lib/api/bots";
import {
  deleteDocument,
  listDocuments,
  subscribeDocuments,
  uploadDocument,
  validateFile,
} from "@/lib/api/documents";
import { formatBytes, timeAgo } from "@/lib/utils/format";
import type { Bot } from "@/types/bot";
import type { DocumentItem, DocumentStatus } from "@/types/document";

const tone: Record<DocumentStatus, "live" | "processing" | "error"> = {
  uploading: "processing",
  processing: "processing",
  ready: "live",
  failed: "error",
};

const label: Record<DocumentStatus, string> = {
  uploading: "Uploading",
  processing: "Processing",
  ready: "Ready",
  failed: "Failed",
};

export default function DocumentsView() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [bots, setBots] = useState<Bot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [targetBot, setTargetBot] = useState("");
  const [filterBot, setFilterBot] = useState("all");
  const [dragActive, setDragActive] = useState(false);
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);
  const [toDelete, setToDelete] = useState<DocumentItem | null>(null);
  const [deleting, setDeleting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);
    Promise.all([listDocuments(), listBots()])
      .then(([d, b]) => {
        if (cancelled) return;
        setDocs(d);
        setBots(b);
        setTargetBot((current) => current || b[0]?.id || "");
      })
      .catch(() => !cancelled && setError(true))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  useEffect(() => subscribeDocuments(setDocs), []);

  const visible = useMemo(
    () => (filterBot === "all" ? docs : docs.filter((d) => d.botId === filterBot)),
    [docs, filterBot]
  );

  function handleFiles(files: FileList | File[]) {
    const bot = bots.find((b) => b.id === targetBot);
    if (!bot) {
      setUploadErrors(["Choose a bot to upload to first."]);
      return;
    }
    const errors: string[] = [];
    Array.from(files).forEach((file) => {
      const problem = validateFile(file);
      if (problem) errors.push(problem);
      else uploadDocument(file, bot);
    });
    setUploadErrors(errors);
  }

  async function confirmDelete() {
    if (!toDelete) return;
    setDeleting(true);
    try {
      await deleteDocument(toDelete.id);
      setToDelete(null);
    } finally {
      setDeleting(false);
    }
  }

  const noBots = !loading && !error && bots.length === 0;

  return (
    <div className="mx-auto w-full max-w-[1440px]">
      <PageHeader
        title="Documents"
        description="Sample data for design purposes. Not connected to the backend yet."
      />

      {loading ? (
        <div className="mt-8 space-y-4">
          <Skeleton className="h-44" />
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      ) : error ? (
        <div className="mt-8">
          <EmptyState
            title="Couldn't load your documents"
            description="Something went wrong while fetching your documents."
            action={<Button onClick={() => setAttempt((a) => a + 1)}>Try again</Button>}
          />
        </div>
      ) : noBots ? (
        <div className="mt-8">
          <EmptyState
            icon={<FileText size={32} />}
            title="Create a bot first"
            description="Documents are uploaded to a bot. Create one, then come back to add PDFs."
            action={
              <Link
                href="/dashboard/bots"
                className="inline-flex rounded-full bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground"
              >
                Go to Bots
              </Link>
            }
          />
        </div>
      ) : (
        <>
          <div className="mt-8 max-w-xs">
            <Select
              id="target-bot"
              label="Upload to bot"
              value={targetBot}
              onChange={(e) => setTargetBot(e.target.value)}
            >
              {bots.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </Select>
          </div>

          <div
            role="button"
            tabIndex={0}
            aria-label="Upload PDF files"
            onClick={() => inputRef.current?.click()}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                inputRef.current?.click();
              }
            }}
            onDragOver={(e) => {
              e.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragActive(false);
              handleFiles(e.dataTransfer.files);
            }}
            className={`mt-4 flex cursor-pointer flex-col items-center rounded-2xl border-2 border-dashed px-6 py-12 text-center transition-all duration-200 ${
              dragActive
                ? "scale-[1.01] border-primary bg-primary/10"
                : "border-border bg-surface hover:border-primary/60"
            }`}
          >
            <UploadCloud size={36} className={dragActive ? "text-primary" : "text-muted"} />
            <p className="font-display mt-4 text-lg font-semibold">
              {dragActive ? "Drop to upload" : "Drag and drop PDFs here"}
            </p>
            <p className="mt-1 text-sm text-muted">or click to browse. PDF only, up to 10 MB each.</p>
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf,.pdf"
              multiple
              hidden
              onChange={(e) => {
                if (e.target.files) handleFiles(e.target.files);
                e.target.value = "";
              }}
            />
          </div>

          {uploadErrors.length > 0 && (
            <div className="mt-3 space-y-1 rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-400" role="alert">
              {uploadErrors.map((m) => (
                <p key={m}>{m}</p>
              ))}
            </div>
          )}

          <div className="mt-10 flex flex-wrap items-end justify-between gap-4">
            <h2 className="font-display text-xl font-semibold">Your documents</h2>
            <div className="w-56">
              <Select
                aria-label="Filter by bot"
                value={filterBot}
                onChange={(e) => setFilterBot(e.target.value)}
              >
                <option value="all">All bots</option>
                {bots.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          <div className="mt-4">
            {visible.length === 0 ? (
              <EmptyState
                icon={<FileText size={32} />}
                title="No documents yet"
                description="Upload a PDF above to start training this bot."
              />
            ) : (
              <div className="overflow-x-auto rounded-2xl border border-border bg-surface">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-border font-mono text-xs uppercase tracking-wider text-muted">
                      <th className="px-5 py-4 font-normal">Document</th>
                      <th className="px-5 py-4 font-normal">Bot</th>
                      <th className="px-5 py-4 font-normal">Size</th>
                      <th className="px-5 py-4 font-normal">Status</th>
                      <th className="px-5 py-4 font-normal">Uploaded</th>
                      <th className="px-5 py-4" />
                    </tr>
                  </thead>
                  <tbody>
                    {visible.map((d) => (
                      <tr key={d.id} className="border-b border-border last:border-0">
                        <td className="px-5 py-4">
                          <div className="flex items-start gap-3">
                            <FileText size={18} className="mt-0.5 shrink-0 text-muted" />
                            <div className="min-w-0">
                              <p className="max-w-[280px] truncate font-medium">{d.name}</p>
                              {d.status === "failed" && d.error && (
                                <p className="mt-1 max-w-[320px] text-xs text-red-400">{d.error}</p>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-5 py-4 text-muted">{d.botName}</td>
                        <td className="px-5 py-4 text-muted">{formatBytes(d.sizeBytes)}</td>
                        <td className="px-5 py-4">
                          <div className="flex flex-col items-start gap-2">
                            <Badge tone={tone[d.status]}>
                              {d.status === "uploading" ? `Uploading ${d.progress}%` : label[d.status]}
                            </Badge>
                            {d.status === "uploading" && (
                              <div className="h-1.5 w-28 overflow-hidden rounded-full bg-foreground/10">
                                <div
                                  className="h-full rounded-full bg-primary transition-all duration-150"
                                  style={{ width: `${d.progress}%` }}
                                />
                              </div>
                            )}
                          </div>
                        </td>
                        <td className="px-5 py-4 text-muted">{timeAgo(d.uploadedAt)}</td>
                        <td className="px-5 py-4 text-right">
                          <button
                            onClick={() => setToDelete(d)}
                            aria-label={`Delete ${d.name}`}
                            disabled={d.status === "uploading"}
                            className="rounded-lg p-2 text-muted transition hover:bg-red-500/10 hover:text-red-400 disabled:pointer-events-none disabled:opacity-40"
                          >
                            <Trash2 size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      <Dialog open={!!toDelete} onClose={() => !deleting && setToDelete(null)} title="Delete document">
        <p className="text-sm text-muted">
          Delete <span className="font-medium text-foreground">{toDelete?.name}</span>? The bot will
          stop using it to answer questions.
        </p>
        <div className="mt-6 flex justify-end gap-3">
          <Button variant="ghost" onClick={() => setToDelete(null)} disabled={deleting}>
            Cancel
          </Button>
          <Button variant="danger" onClick={confirmDelete} disabled={deleting}>
            {deleting ? "Deleting..." : "Delete"}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}