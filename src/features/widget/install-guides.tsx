"use client";

import { useMemo, useState } from "react";
import CopyButton from "@/components/ui/copy-button";
import { getGuides, WIDGET_SRC } from "./snippets";

export default function InstallGuides({ widgetKey }: { widgetKey: string }) {
  const guides = useMemo(() => getGuides(widgetKey), [widgetKey]);
  const [active, setActive] = useState(guides[0].id);
  const guide = guides.find((g) => g.id === active) ?? guides[0];

  return (
    <section className="rounded-2xl border border-border bg-surface p-5">
      <h2 className="font-display text-lg font-semibold">Install on your website</h2>
      <p className="mt-1 text-sm text-muted">
        Choose your platform. The script host below is a placeholder until the widget is deployed:
        <span className="ml-1 font-mono text-xs text-foreground">{WIDGET_SRC}</span>
      </p>

      <div role="tablist" aria-label="Platform" className="mt-5 flex flex-wrap gap-2">
        {guides.map((g) => (
          <button
            key={g.id}
            role="tab"
            aria-selected={g.id === active}
            onClick={() => setActive(g.id)}
            className={`rounded-full border px-4 py-2 text-xs font-semibold transition ${
              g.id === active
                ? "border-primary bg-primary/15 text-primary"
                : "border-border text-muted hover:text-foreground"
            }`}
          >
            {g.label}
          </button>
        ))}
      </div>

      <div role="tabpanel" className="mt-5">
        <ol className="list-decimal space-y-2 pl-5 text-sm text-muted">
          {guide.steps.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ol>

        <div className="mt-5 overflow-hidden rounded-xl border border-border bg-background">
          <div className="flex items-center justify-between border-b border-border px-4 py-2">
            <span className="font-mono text-xs text-muted">{guide.filename ?? "snippet"}</span>
            <CopyButton text={guide.code} label="Copy code" />
          </div>
          <pre className="overflow-x-auto p-4 font-mono text-xs leading-relaxed" data-lenis-prevent>
            <code>{guide.code}</code>
          </pre>
        </div>

        {guide.note && <p className="mt-3 text-xs text-muted">{guide.note}</p>}
      </div>
    </section>
  );
}