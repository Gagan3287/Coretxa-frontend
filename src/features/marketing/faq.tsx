"use client";

import { useState } from "react";
import { Plus } from "lucide-react";

const items = [
  { q: "What can I upload?", a: "Cortexa currently accepts PDF documents." },
  { q: "How does Cortexa answer questions?", a: "The assistant answers using the documents you upload, and it can show which document an answer came from." },
  { q: "What if the answer isn't in my documents?", a: "The assistant tells the visitor it couldn't find an answer, so they can rephrase or contact you." },
  { q: "Where can I add the chat?", a: "On almost any website. Use a script tag, an iframe or a hosted chat page. The dashboard has step-by-step guides for HTML, PHP, WordPress, React, Next.js, Shopify, Wix, Squarespace and Google Tag Manager." },
  { q: "Can I match my brand?", a: "Yes. You can set the display name, greeting, color and position, and preview changes before saving." },
];

export default function Faq() {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <section id="faq" className="mx-auto w-full max-w-3xl px-6 py-32 md:px-8">
      <p className="font-mono text-sm tracking-widest text-secondary">FAQ</p>
      <h2 className="font-display mt-4 text-[clamp(2.25rem,5vw,4rem)] font-bold leading-none tracking-tight">
        Questions, <span className="gradient-text">answered.</span>
      </h2>

      <div className="mt-12">
        {items.map((item, i) => {
          const isOpen = open === i;
          return (
            <div key={item.q} className="border-b border-border first:border-t">
              <h3>
                <button
                  id={`faq-btn-${i}`}
                  aria-expanded={isOpen}
                  aria-controls={`faq-panel-${i}`}
                  onClick={() => setOpen(isOpen ? null : i)}
                  className="flex w-full items-center justify-between gap-6 py-6 text-left"
                >
                  <span className="font-display text-lg font-semibold md:text-xl">{item.q}</span>
                  <Plus
                    size={22}
                    className={`shrink-0 text-primary transition-transform duration-300 ${isOpen ? "rotate-45" : ""}`}
                  />
                </button>
              </h3>
              <div
                id={`faq-panel-${i}`}
                role="region"
                aria-labelledby={`faq-btn-${i}`}
                className={`grid transition-[grid-template-rows] duration-300 ease-out ${
                  isOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
                }`}
              >
                <div className="overflow-hidden">
                  <p className="pb-6 text-muted">{item.a}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}