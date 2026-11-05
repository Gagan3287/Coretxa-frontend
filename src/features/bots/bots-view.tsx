"use client";

import { useEffect, useMemo, useState } from "react";
import { Bot as BotIcon, Plus, Search } from "lucide-react";
import Badge from "@/components/ui/badge";
import Button from "@/components/ui/button";
import Card from "@/components/ui/card";
import EmptyState from "@/components/ui/empty-state";
import PageHeader from "@/components/ui/page-header";
import Skeleton from "@/components/ui/skeleton";
import { listBots } from "@/lib/api/bots";
import { timeAgo } from "@/lib/utils/format";
import type { Bot, BotStatus } from "@/types/bot";
import CreateBotDialog from "./create-bot-dialog";

const statusTone: Record<BotStatus, "live" | "processing" | "error"> = {
  active: "live",
  processing: "processing",
  failed: "error",
};

const statusLabel: Record<BotStatus, string> = {
  active: "Active",
  processing: "Processing",
  failed: "Failed",
};

export default function BotsView() {
  const [bots, setBots] = useState<Bot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [query, setQuery] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    listBots()
      .then((data) => !cancelled && setBots(data))
      .catch(() => !cancelled && setError(true))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return bots;
    return bots.filter(
      (b) => b.name.toLowerCase().includes(q) || b.description.toLowerCase().includes(q)
    );
  }, [bots, query]);

  const newBotButton = (
    <Button onClick={() => setDialogOpen(true)}>
      <Plus size={16} /> New bot
    </Button>
  );

  return (
    <div className="mx-auto w-full max-w-[1440px]">
      <PageHeader
        title="Bots"
        description="Create and manage your AI bots. Each bot can be trained on your documents."
        actions={newBotButton}
      />

      <div className="relative mt-8 max-w-md">
        <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-muted" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search bots"
          aria-label="Search bots"
          className="w-full rounded-full border border-border bg-surface py-3 pl-11 pr-4 text-sm outline-none transition placeholder:text-muted/60 focus:border-primary focus:ring-2 focus:ring-primary/30"
        />
      </div>

      <div className="mt-6">
        {loading ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-40" />
            ))}
          </div>
        ) : error ? (
          <EmptyState
            title="Couldn't load your bots"
            description="Something went wrong while fetching your bots."
            action={
              <Button
                onClick={() => {
                  setLoading(true);
                  setError(false);
                  setAttempt((a) => a + 1);
                }}
              >
                Try again
              </Button>
            }
          />
        ) : bots.length === 0 ? (
          <EmptyState
            icon={<BotIcon size={32} />}
            title="No bots yet"
            description="Create your first bot, then upload documents to train it."
            action={newBotButton}
          />
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<Search size={32} />}
            title="No matching bots"
            description={`Nothing matches "${query}". Try a different search.`}
          />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {filtered.map((b) => (
              <Card
                key={b.id}
                className="transition-all duration-200 hover:-translate-y-1 hover:border-primary/50"
              >
                <div className="flex items-start justify-between gap-3">
                  <h3 className="font-semibold">{b.name}</h3>
                  <Badge tone={statusTone[b.status]}>{statusLabel[b.status]}</Badge>
                </div>
                <p className="mt-3 line-clamp-2 min-h-10 text-sm text-muted">
                  {b.description || "No description."}
                </p>
                <div className="mt-5 flex items-center justify-between text-xs text-muted">
                  <span>{b.documentCount} documents</span>
                  <span>Updated {timeAgo(b.updatedAt)}</span>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <CreateBotDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onCreated={(bot) => {
          setBots((prev) => [bot, ...prev]);
          setDialogOpen(false);
        }}
      />
    </div>
  );
}