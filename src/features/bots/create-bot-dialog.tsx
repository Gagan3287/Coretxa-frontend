"use client";

import { useState } from "react";
import Button from "@/components/ui/button";
import Dialog from "@/components/ui/dialog";
import Input from "@/components/ui/input";
import Textarea from "@/components/ui/textarea";
import { createBot } from "@/lib/api/bots";
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
  const [errors, setErrors] = useState<{ name?: string; description?: string }>({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function reset() {
    setName("");
    setDescription("");
    setErrors({});
    setFormError("");
  }

  function close() {
    if (submitting) return;
    reset();
    onClose();
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
      const bot = await createBot({ name: trimmed, description });
      reset();
      onCreated(bot);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onClose={close} title="Create bot">
      <form onSubmit={submit} className="space-y-5" noValidate>
        <Input
          id="bot-name"
          label="Bot name"
          placeholder="e.g. Customer Support"
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
          placeholder="What will this bot help people with?"
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
            {submitting ? "Creating..." : "Create bot"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}