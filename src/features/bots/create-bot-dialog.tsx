"use client";

import { useState } from "react";
import { Check, Copy, KeyRound, Sparkles } from "lucide-react";
import Button from "@/components/ui/button";
import Dialog from "@/components/ui/dialog";
import Input from "@/components/ui/input";
import Textarea from "@/components/ui/textarea";
import { createBot } from "@/lib/api/bots";
import { BOT_LOGOS, getBotLogo } from "@/config/bot-logos";
import type { Bot } from "@/types/bot";

export default function CreateBotDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (bot: Bot) => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedAvatar, setSelectedAvatar] = useState<string>(BOT_LOGOS[0].id);
  const [errors, setErrors] = useState<{ name?: string; description?: string }>({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Widget key reveal state — shown after successful creation
  const [widgetKey, setWidgetKey] = useState<string | null>(null);
  const [createdBot, setCreatedBot] = useState<Bot | null>(null);
  const [copied, setCopied] = useState(false);

  function reset() {
    setName("");
    setDescription("");
    setSelectedAvatar(BOT_LOGOS[0].id);
    setErrors({});
    setFormError("");
    setWidgetKey(null);
    setCreatedBot(null);
    setCopied(false);
  }

  function close() {
    if (submitting) return;
    if (createdBot) {
      onCreated(createdBot);
    }
    reset();
    onClose();
  }

  async function copyKey() {
    if (!widgetKey) return;
    try {
      await navigator.clipboard.writeText(widgetKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // fallback: nothing
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const next: typeof errors = {};
    const trimmed = name.trim();
    if (trimmed.length < 2) next.name = "Name must be at least 2 characters.";
    else if (trimmed.length > 40) next.name = "Name must be 40 characters or fewer.";
    if (description.length > 160) next.description = "Description must be 160 characters or fewer.";
    setErrors(next);
    setFormError("");
    if (Object.keys(next).length) return;

    setSubmitting(true);
    try {
      const bot = await createBot({ name: trimmed, description, avatar: selectedAvatar });
      setCreatedBot(bot);
      if (bot.widgetKey) {
        setWidgetKey(bot.widgetKey);
      } else {
        reset();
        onCreated(bot);
      }
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  const activeLogo = getBotLogo(selectedAvatar);

  // ── Widget key reveal screen ─────────────────────────────────────────────
  if (widgetKey && createdBot) {
    return (
      <Dialog open={open} onClose={close} title="Bot created — save your widget key">
        <div className="space-y-5">
          <div className="rounded-xl bg-amber-500/10 border border-amber-500/30 px-4 py-3 text-sm text-amber-400">
            <strong>This key is shown only once.</strong> Copy it now — you cannot retrieve it again from the dashboard.
          </div>

          <div>
            <div className="flex items-center gap-3 mb-3">
              <div
                className="h-10 w-10 shrink-0"
                dangerouslySetInnerHTML={{ __html: getBotLogo(createdBot.avatar).svg }}
              />
              <div>
                <p className="font-semibold text-foreground text-sm">{createdBot.name}</p>
                <p className="text-xs text-muted">Use this widget key to embed the chat on your website:</p>
              </div>
            </div>

            <div className="flex items-center gap-2 rounded-xl border border-border bg-surface px-4 py-3 font-mono text-xs break-all">
              <KeyRound size={14} className="shrink-0 text-muted" />
              <span className="flex-1 select-all">{widgetKey}</span>
              <button
                type="button"
                aria-label="Copy widget key"
                onClick={copyKey}
                className="ml-2 shrink-0 rounded-lg p-1.5 text-muted hover:bg-primary/10 hover:text-primary transition-colors"
              >
                {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
              </button>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button onClick={close}>Done — I&apos;ve saved my key</Button>
          </div>
        </div>
      </Dialog>
    );
  }

  // ── Creation form ────────────────────────────────────────────────────────
  return (
    <Dialog open={open} onClose={close} title="Create AI Bot">
      <form onSubmit={submit} className="space-y-5" noValidate>
        {/* 10 Bot Logos Selector */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted">
              Choose Bot Avatar Logo
            </label>
            <span className="font-mono text-xs text-secondary font-medium">
              {activeLogo.name}
            </span>
          </div>

          <div className="grid grid-cols-5 gap-2.5 rounded-2xl border border-border/80 bg-background/50 p-3">
            {BOT_LOGOS.map((logo) => {
              const isSelected = logo.id === selectedAvatar;
              return (
                <button
                  key={logo.id}
                  type="button"
                  onClick={() => setSelectedAvatar(logo.id)}
                  title={`${logo.name} (${logo.badge})`}
                  className={`relative flex flex-col items-center justify-center rounded-xl p-2 transition-all ${
                    isSelected
                      ? "bg-primary/20 ring-2 ring-secondary shadow-md scale-105"
                      : "bg-surface/60 hover:bg-surface hover:scale-102 border border-border/40 opacity-75 hover:opacity-100"
                  }`}
                >
                  <div
                    className="h-8 w-8"
                    dangerouslySetInnerHTML={{ __html: logo.svg }}
                  />
                  <span className="mt-1 font-mono text-[9px] text-muted truncate max-w-full">
                    {logo.badge}
                  </span>
                  {isSelected && (
                    <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-secondary text-background">
                      <Check size={10} className="stroke-[3]" />
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <Input
          id="bot-name"
          label="Bot name"
          placeholder="e.g. Customer Support AI"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            if (formError) setFormError("");
            if (errors.name) setErrors((prev) => ({ ...prev, name: undefined }));
          }}
          error={errors.name}
          autoFocus
        />

        <Textarea
          id="bot-description"
          label="Description (optional)"
          placeholder="What will this AI assistant help people with?"
          value={description}
          onChange={(e) => {
            setDescription(e.target.value);
            if (errors.description) setErrors((prev) => ({ ...prev, description: undefined }));
          }}
          error={errors.description}
          hint={`${description.length}/160`}
        />

        {formError && (
          <p className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-400" role="alert">
            {formError}
          </p>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="ghost" onClick={close} disabled={submitting}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? "Creating..." : "Create Bot"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
