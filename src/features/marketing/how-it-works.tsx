"use client";

import { useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";
import { FileText, MessageCircle } from "lucide-react";
import Badge from "@/components/ui/badge";
import { readableTextOn } from "@/lib/utils/origin";

gsap.registerPlugin(useGSAP, ScrollTrigger);

const steps = [
  { n: "01", title: "Build", text: "Upload your PDFs. Cortexa processes them so your assistant can answer from your content." },
  { n: "02", title: "Customize", text: "Name it, pick your brand color and write a greeting. See every change in a live preview." },
  { n: "03", title: "Deploy", text: "Paste one snippet into your site, or use an iframe or a hosted chat page." },
];

const swatches = ["#4f46e5", "#0891b2", "#059669", "#e11d48", "#d97706"];
const platforms = ["HTML", "PHP", "WordPress", "React", "Next.js", "Shopify", "Wix", "Squarespace", "Tag Manager"];

export default function HowItWorks() {
  const root = useRef<HTMLElement>(null);
  const stage = useRef<HTMLDivElement>(null);
  const progress = useRef<HTMLDivElement>(null);
  const trigger = useRef<ScrollTrigger | null>(null);
  const [active, setActive] = useState(0);
  const [swatch, setSwatch] = useState(swatches[0]);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(min-width: 1024px) and (prefers-reduced-motion: no-preference)", () => {
        trigger.current = ScrollTrigger.create({
          trigger: stage.current,
          start: "top top",
          end: () => "+=" + window.innerHeight * 2.2,
          pin: true,
          anticipatePin: 1,
          invalidateOnRefresh: true,
          onUpdate: (self) => {
            const i = Math.min(steps.length - 1, Math.floor(self.progress * steps.length));
            setActive((prev) => (prev === i ? prev : i));
            gsap.set(progress.current, { scaleY: self.progress });
          },
        });
        return () => {
          trigger.current = null;
        };
      });
      return () => mm.revert();
    },
    { scope: root }
  );

  function go(i: number) {
    const st = trigger.current;
    if (st) {
      window.scrollTo({ top: st.start + (st.end - st.start) * (i / steps.length) + 2 });
    } else {
      setActive(i);
    }
  }

  const panel = (i: number) =>
    `absolute inset-0 p-6 transition-all duration-500 md:p-8 ${
      active === i ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-6 opacity-0"
    }`;

  return (
    <section id="how" ref={root} className="relative">
      <div
        ref={stage}
        className="mx-auto flex w-full max-w-[1440px] flex-col justify-center gap-10 px-6 py-24 md:px-8 lg:h-screen lg:flex-row lg:items-center lg:gap-16 lg:py-0"
      >
        <div className="lg:w-1/2">
          <p className="font-mono text-sm tracking-widest text-secondary">HOW IT WORKS</p>
          <h2 className="font-display mt-4 text-[clamp(2.25rem,5vw,4.5rem)] font-bold leading-none tracking-tight">
            Three steps to <span className="gradient-text">live.</span>
          </h2>

          <div className="relative mt-10 space-y-3 lg:pl-8">
            <div className="absolute bottom-0 left-0 top-0 hidden w-px bg-border lg:block">
              <div ref={progress} className="h-full origin-top scale-y-0 bg-primary" />
            </div>
            {steps.map((s, i) => (
              <button
                key={s.n}
                onClick={() => go(i)}
                aria-current={active === i}
                className={`block w-full rounded-2xl border p-5 text-left transition-all duration-300 ${
                  active === i
                    ? "border-primary/60 bg-primary/10"
                    : "border-border opacity-60 hover:opacity-100"
                }`}
              >
                <span className="font-mono text-xs text-secondary">{s.n}</span>
                <h3 className="font-display mt-2 text-2xl font-bold">{s.title}</h3>
                <p className="mt-2 text-sm text-muted">{s.text}</p>
              </button>
            ))}
          </div>
        </div>

        <div className="relative h-[440px] w-full overflow-hidden rounded-3xl border border-border bg-surface lg:w-1/2">
          <div className={panel(0)} aria-hidden={active !== 0}>
            <p className="font-mono text-xs text-muted">YOUR DOCUMENTS (EXAMPLE)</p>
            <div className="mt-5 space-y-3">
              {[
                { name: "Refund-policy.pdf", tone: "live" as const, label: "Ready", fill: "100%" },
                { name: "Employee-handbook.pdf", tone: "live" as const, label: "Ready", fill: "100%" },
                { name: "API-reference.pdf", tone: "processing" as const, label: "Processing", fill: "68%" },
              ].map((d) => (
                <div key={d.name} className="rounded-xl border border-border p-4">
                  <div className="flex items-center justify-between gap-3">
                    <span className="flex min-w-0 items-center gap-3 text-sm">
                      <FileText size={18} className="shrink-0 text-muted" />
                      <span className="truncate">{d.name}</span>
                    </span>
                    <Badge tone={d.tone}>{d.label}</Badge>
                  </div>
                  <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-foreground/10">
                    <div
                      className="h-full rounded-full bg-primary transition-[width] duration-1000 ease-out"
                      style={{ width: active === 0 ? d.fill : "0%" }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className={panel(1)} aria-hidden={active !== 1}>
            <p className="font-mono text-xs text-muted">BRAND COLOR, TRY IT</p>
            <div className="mt-5 flex gap-3">
              {swatches.map((c) => (
                <button
                  key={c}
                  aria-label={`Use color ${c}`}
                  onClick={() => setSwatch(c)}
                  className={`h-9 w-9 rounded-full transition-transform hover:scale-110 ${
                    swatch === c ? "ring-2 ring-foreground ring-offset-2 ring-offset-surface" : ""
                  }`}
                  style={{ background: c }}
                />
              ))}
            </div>
            <div className="mt-8 flex items-end justify-between gap-4">
              <div className="max-w-[240px] space-y-2 text-sm">
                <div className="rounded-2xl rounded-tl-sm bg-foreground/10 px-4 py-2">
                  Hi! Ask me anything about our docs.
                </div>
                <div
                  className="ml-auto w-fit rounded-2xl rounded-tr-sm px-4 py-2 transition-colors duration-300"
                  style={{ background: swatch, color: readableTextOn(swatch) }}
                >
                  How do I get started?
                </div>
              </div>
              <div
                className="grid h-14 w-14 shrink-0 place-items-center rounded-full shadow-lg transition-colors duration-300"
                style={{ background: swatch, color: readableTextOn(swatch) }}
              >
                <MessageCircle size={24} />
              </div>
            </div>
          </div>

          <div className={panel(2)} aria-hidden={active !== 2}>
            <p className="font-mono text-xs text-muted">ONE SNIPPET (EXAMPLE)</p>
            <pre className="mt-5 overflow-x-auto rounded-xl border border-border bg-background p-4 font-mono text-xs leading-relaxed">
              <code>{`<script
  src=".../cortexa-widget.js"
  data-widget-key="YOUR_KEY"
  async
></script>`}</code>
            </pre>
            <p className="mt-6 font-mono text-xs text-muted">STEP-BY-STEP GUIDES FOR</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {platforms.map((p) => (
                <span key={p} className="rounded-full border border-border px-3 py-1.5 text-xs text-muted">
                  {p}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}