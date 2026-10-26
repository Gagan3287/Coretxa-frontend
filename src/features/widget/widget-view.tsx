"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Code } from "lucide-react";
import Button from "@/components/ui/button";
import CopyButton from "@/components/ui/copy-button";
import EmptyState from "@/components/ui/empty-state";
import Input from "@/components/ui/input";
import PageHeader from "@/components/ui/page-header";
import Segmented from "@/components/ui/segmented";
import Select from "@/components/ui/select";
import Skeleton from "@/components/ui/skeleton";
import Textarea from "@/components/ui/textarea";
import { listBots } from "@/lib/api/bots";
import { getWidgetConfig, saveWidgetConfig } from "@/lib/api/widget";
import type { Bot } from "@/types/bot";
import type { WidgetConfig } from "@/types/widget";
import AllowedWebsites from "./allowed-websites";
import EmbedOptions from "./embed-options";
import InstallGuides from "./install-guides";
import WidgetPreview from "./widget-preview";

export default function WidgetView() {
  const [bots, setBots] = useState<Bot[]>([]);
  const [botsLoading, setBotsLoading] = useState(true);
  const [botsError, setBotsError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [botId, setBotId] = useState("");

  const [saved, setSaved] = useState<WidgetConfig | null>(null);
  const [draft, setDraft] = useState<WidgetConfig | null>(null);
  const [cfgLoading, setCfgLoading] = useState(false);
  const [cfgError, setCfgError] = useState(false);
  const [cfgAttempt, setCfgAttempt] = useState(0);

  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<"" | "saved" | "error">("");

  useEffect(() => {
    let cancelled = false;
    setBotsLoading(true);
    setBotsError(false);
    listBots()
      .then((data) => {
        if (cancelled) return;
        setBots(data);
        setBotId((current) => current || data[0]?.id || "");
      })
      .catch(() => !cancelled && setBotsError(true))
      .finally(() => !cancelled && setBotsLoading(false));
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  useEffect(() => {
    const bot = bots.find((b) => b.id === botId);
    if (!bot) return;
    let cancelled = false;
    setCfgLoading(true);
    setCfgError(false);
    getWidgetConfig(bot)
      .then((c) => {
        if (cancelled) return;
        setSaved(c);
        setDraft(c);
      })
      .catch(() => !cancelled && setCfgError(true))
      .finally(() => !cancelled && setCfgLoading(false));
    return () => {
      cancelled = true;
    };
  }, [botId, bots, cfgAttempt]);

  const dirty = useMemo(() => JSON.stringify(saved) !== JSON.stringify(draft), [saved, draft]);

  const errors = useMemo(() => {
    const e: { displayName?: string; greeting?: string } = {};
    if (draft) {
      if (!draft.displayName.trim()) e.displayName = "Display name is required.";
      else if (draft.displayName.length > 40) e.displayName = "Keep it to 40 characters or fewer.";
      if (draft.greeting.length > 160) e.greeting = "Keep it to 160 characters or fewer.";
    }
    return e;
  }, [draft]);

  const valid = Object.keys(errors).length === 0;

  function update(patch: Partial<WidgetConfig>) {
    setDraft((d) => (d ? { ...d, ...patch } : d));
    setStatus("");
  }

  function changeBot(id: string) {
    if (dirty && !window.confirm("Discard your unsaved changes?")) return;
    setStatus("");
    setBotId(id);
  }

  async function save() {
    if (!draft || !valid) return;
    setSaving(true);
    setStatus("");
    try {
      const result = await saveWidgetConfig(draft);
      setSaved(result);
      setDraft(result);
      setStatus("saved");
    } catch {
      setStatus("error");
    } finally {
      setSaving(false);
    }
  }

  const headerActions = (
    <div className="flex items-center gap-3">
      {status === "saved" && (
        <span role="status" className="text-xs text-secondary">
          Saved
        </span>
      )}
      {status === "error" && (
        <span role="alert" className="text-xs text-red-400">
          Couldn&apos;t save. Try again.
        </span>
      )}
      <Button variant="ghost" disabled={!dirty || saving} onClick={() => setDraft(saved)}>
        Discard
      </Button>
      <Button disabled={!dirty || !valid || saving} onClick={save}>
        {saving ? "Saving..." : "Save changes"}
      </Button>
    </div>
  );

  return (
    <div className="mx-auto w-full max-w-[1440px]">
      <PageHeader
        title="Widget & Embed"
        description="Sample data for design purposes. Not connected to the backend yet."
        actions={bots.length > 0 ? headerActions : undefined}
      />

      {botsLoading ? (
        <div className="mt-8 space-y-4">
          <Skeleton className="h-16 max-w-xs" />
          <Skeleton className="h-96" />
        </div>
      ) : botsError ? (
        <div className="mt-8">
          <EmptyState
            title="Couldn't load your bots"
            description="Something went wrong while fetching your bots."
            action={<Button onClick={() => setAttempt((a) => a + 1)}>Try again</Button>}
          />
        </div>
      ) : bots.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            icon={<Code size={32} />}
            title="Create a bot first"
            description="The widget belongs to a bot. Create one, then come back to deploy it."
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
            <Select id="widget-bot" label="Bot" value={botId} onChange={(e) => changeBot(e.target.value)}>
              {bots.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </Select>
          </div>

          {cfgLoading || !draft ? (
            cfgError ? (
              <div className="mt-8">
                <EmptyState
                  title="Couldn't load widget settings"
                  action={<Button onClick={() => setCfgAttempt((a) => a + 1)}>Try again</Button>}
                />
              </div>
            ) : (
              <div className="mt-8 grid gap-6 lg:grid-cols-2">
                <Skeleton className="h-[520px]" />
                <Skeleton className="h-[520px]" />
              </div>
            )
          ) : (
            <div className="mt-8 space-y-6">
              <div className="grid items-start gap-6 lg:grid-cols-2">
                <div className="space-y-6">
                  <section className="space-y-5 rounded-2xl border border-border bg-surface p-5">
                    <h2 className="font-display text-lg font-semibold">Widget settings</h2>
                    <Input
                      id="display-name"
                      label="Display name"
                      value={draft.displayName}
                      onChange={(e) => update({ displayName: e.target.value })}
                      error={errors.displayName}
                    />
                    <Textarea
                      id="greeting"
                      label="Welcome greeting"
                      value={draft.greeting}
                      onChange={(e) => update({ greeting: e.target.value })}
                      error={errors.greeting}
                      hint={`${draft.greeting.length}/160`}
                    />
                    <div className="flex flex-wrap items-end gap-8">
                      <div className="flex flex-col gap-2">
                        <label htmlFor="brand-color" className="font-mono text-xs uppercase tracking-wider text-muted">
                          Brand color
                        </label>
                        <div className="flex items-center gap-3">
                          <input
                            id="brand-color"
                            type="color"
                            value={draft.color}
                            onChange={(e) => update({ color: e.target.value })}
                            className="h-11 w-16 cursor-pointer rounded-lg border border-border bg-surface p-1"
                          />
                          <span className="font-mono text-xs text-muted">{draft.color.toUpperCase()}</span>
                        </div>
                      </div>
                      <div className="flex flex-col gap-2">
                        <span className="font-mono text-xs uppercase tracking-wider text-muted">Position</span>
                        <Segmented
                          label="Widget position"
                          value={draft.position}
                          onChange={(v) => update({ position: v })}
                          options={[
                            { value: "left", label: "Bottom left" },
                            { value: "right", label: "Bottom right" },
                          ]}
                        />
                      </div>
                    </div>
                  </section>

                  <section className="rounded-2xl border border-border bg-surface p-5">
                    <h2 className="font-display text-lg font-semibold">Widget key</h2>
                    <div className="mt-4 flex flex-wrap items-center gap-3">
                      <code className="rounded-xl border border-border bg-background px-4 py-2 font-mono text-xs">
                        {draft.widgetKey}
                      </code>
                      <CopyButton text={draft.widgetKey} label="Copy key" />
                      <Button variant="outline" size="sm" disabled title="Available once the backend supports it">
                        Regenerate
                      </Button>
                    </div>
                    <p className="mt-3 text-xs text-muted">
                      Mock key. A widget key is visible in your page&apos;s HTML, so treat it as public, not
                      secret. The backend restricts where it works.
                    </p>
                  </section>

                  <AllowedWebsites
                    origins={draft.allowedOrigins}
                    onChange={(next) => update({ allowedOrigins: next })}
                  />
                </div>

                <div className="lg:sticky lg:top-24">
                  <WidgetPreview config={draft} />
                </div>
              </div>

              <InstallGuides widgetKey={draft.widgetKey} />
              <EmbedOptions hostedUrl={draft.hostedUrl} />
            </div>
          )}
        </>
      )}
    </div>
  );
}