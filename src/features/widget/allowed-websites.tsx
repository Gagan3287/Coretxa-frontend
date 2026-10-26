"use client";

import { useState } from "react";
import { Globe, X } from "lucide-react";
import Button from "@/components/ui/button";
import Input from "@/components/ui/input";
import { normalizeOrigin } from "@/lib/utils/origin";

const MAX_ORIGINS = 20;

export default function AllowedWebsites({
  origins,
  onChange,
}: {
  origins: string[];
  onChange: (next: string[]) => void;
}) {
  const [value, setValue] = useState("");
  const [error, setError] = useState("");

  function add(e: React.FormEvent) {
    e.preventDefault();
    const { origin, error: problem } = normalizeOrigin(value);
    if (problem || !origin) {
      setError(problem ?? "Invalid address.");
      return;
    }
    if (origins.includes(origin)) {
      setError("That website is already in the list.");
      return;
    }
    if (origins.length >= MAX_ORIGINS) {
      setError(`You can add up to ${MAX_ORIGINS} websites.`);
      return;
    }
    onChange([...origins, origin]);
    setValue("");
    setError("");
  }

  return (
    <section className="rounded-2xl border border-border bg-surface p-5">
      <h2 className="font-display text-lg font-semibold">Allowed websites</h2>
      <p className="mt-1 text-sm text-muted">
        Websites where this bot&apos;s widget is meant to run. Only the origin is stored, so paths are
        ignored.
      </p>

      <form onSubmit={add} className="mt-4 flex items-start gap-3" noValidate>
        <div className="flex-1">
          <Input
            id="origin"
            aria-label="Website address"
            placeholder="https://example.com"
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              if (error) setError("");
            }}
            error={error}
          />
        </div>
        <Button type="submit" variant="outline">
          Add
        </Button>
      </form>

      <ul className="mt-4 space-y-2">
        {origins.length === 0 ? (
          <li className="rounded-xl border border-dashed border-border px-4 py-6 text-center text-sm text-muted">
            No websites added yet.
          </li>
        ) : (
          origins.map((o) => (
            <li
              key={o}
              className="flex items-center justify-between gap-3 rounded-xl border border-border px-4 py-3 text-sm"
            >
              <span className="flex min-w-0 items-center gap-2">
                <Globe size={16} className="shrink-0 text-muted" />
                <span className="truncate font-mono text-xs">{o}</span>
              </span>
              <button
                aria-label={`Remove ${o}`}
                onClick={() => onChange(origins.filter((x) => x !== o))}
                className="rounded-lg p-1.5 text-muted transition hover:bg-red-500/10 hover:text-red-400"
              >
                <X size={16} />
              </button>
            </li>
          ))
        )}
      </ul>

      <p className="mt-4 rounded-xl bg-primary/10 px-4 py-3 text-xs text-muted">
        Mock setting. Hiding the widget in the browser is not real security. The backend must enforce
        which origins can use this bot.
      </p>
    </section>
  );
}