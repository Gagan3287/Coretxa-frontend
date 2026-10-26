"use client";

import { useState } from "react";
import { MessageCircle, ThumbsDown, ThumbsUp, X } from "lucide-react";
import Segmented from "@/components/ui/segmented";
import { readableTextOn } from "@/lib/utils/origin";
import type { WidgetConfig } from "@/types/widget";

type Scenario = "closed" | "answer" | "unknown";

export default function WidgetPreview({
  config,
}: {
  config: Pick<WidgetConfig, "displayName" | "greeting" | "color" | "position">;
}) {
  const [scenario, setScenario] = useState<Scenario>("answer");
  const [device, setDevice] = useState<"desktop" | "mobile">("desktop");

  const open = scenario !== "closed";
  const mobile = device === "mobile";
  const onColor = readableTextOn(config.color);
  const side = config.position === "right" ? "right-4" : "left-4";

  return (
    <div className="rounded-2xl border border-border bg-surface p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-lg font-semibold">Live preview</h2>
        <Segmented
          label="Preview device"
          value={device}
          onChange={setDevice}
          options={[
            { value: "desktop", label: "Desktop" },
            { value: "mobile", label: "Mobile" },
          ]}
        />
      </div>
      <div className="mt-3">
        <Segmented
          label="Preview state"
          value={scenario}
          onChange={setScenario}
          options={[
            { value: "closed", label: "Collapsed" },
            { value: "answer", label: "Answer" },
            { value: "unknown", label: "Unknown answer" },
          ]}
        />
      </div>

      <div
        className={`relative mx-auto mt-5 overflow-hidden rounded-xl border border-border bg-foreground/5 ${
          mobile ? "h-[540px] w-[300px]" : "h-[480px] w-full"
        }`}
      >
        <div className="space-y-3 p-5" aria-hidden="true">
          <div className="h-3 w-1/3 rounded bg-foreground/10" />
          <div className="h-3 w-2/3 rounded bg-foreground/10" />
          <div className="h-3 w-1/2 rounded bg-foreground/10" />
        </div>

        {open && (
          <div
            className={`absolute flex flex-col overflow-hidden rounded-2xl bg-white text-slate-800 shadow-2xl ${
              mobile ? "inset-x-2 bottom-20 top-2" : `bottom-20 top-4 w-[320px] max-w-[calc(100%-2rem)] ${side}`
            }`}
          >
            <div
              className="flex items-center justify-between px-4 py-3"
              style={{ background: config.color, color: onColor }}
            >
              <span className="truncate text-sm font-semibold">{config.displayName || "Assistant"}</span>
              <button aria-label="Close preview chat" onClick={() => setScenario("closed")}>
                <X size={18} />
              </button>
            </div>

            <div className="flex-1 space-y-3 overflow-y-auto p-4 text-sm">
              <div className="max-w-[85%] rounded-2xl rounded-tl-sm bg-slate-100 px-3 py-2">
                {config.greeting || "Hi! How can I help?"}
              </div>
              <div
                className="ml-auto max-w-[85%] rounded-2xl rounded-tr-sm px-3 py-2"
                style={{ background: config.color, color: onColor }}
              >
                {scenario === "answer" ? "What is your refund policy?" : "Do you ship to Mars?"}
              </div>
              <div className="max-w-[90%] rounded-2xl rounded-tl-sm bg-slate-100 px-3 py-2">
                {scenario === "answer" ? (
                  <>
                    <p>Refunds can be requested within the window described in your policy document.</p>
                    <span className="mt-2 inline-block rounded-full bg-white px-2 py-1 font-mono text-[10px] text-slate-600">
                      Refund-policy.pdf · p. 2
                    </span>
                  </>
                ) : (
                  <p>
                    I couldn&apos;t find that in the documents I have. Try rephrasing, or contact the team
                    directly.
                  </p>
                )}
              </div>
              {scenario === "answer" && (
                <div className="flex gap-2 text-slate-400">
                  <ThumbsUp size={14} aria-label="Helpful" />
                  <ThumbsDown size={14} aria-label="Not helpful" />
                </div>
              )}
            </div>

            <div className="border-t border-slate-200 px-4 py-3 text-xs text-slate-400">Ask a question...</div>
          </div>
        )}

        <button
          aria-label={open ? "Close chat" : "Open chat"}
          onClick={() => setScenario(open ? "closed" : "answer")}
          className={`absolute bottom-4 grid h-14 w-14 place-items-center rounded-full shadow-lg transition-transform hover:scale-105 ${side}`}
          style={{ background: config.color, color: onColor }}
        >
          <MessageCircle size={24} />
        </button>
      </div>
      <p className="mt-3 text-xs text-muted">Sample conversation for illustration. Not real answers.</p>
    </div>
  );
}