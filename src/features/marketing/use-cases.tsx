"use client";

import { useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";
import { ArrowUpRight } from "lucide-react";

gsap.registerPlugin(useGSAP, ScrollTrigger);

const cases = [
  { name: "Customer Support", q: "How do I update my billing details?", a: "Open Billing in your account settings and choose Update payment method.", src: "Help-center.pdf · p. 6" },
  { name: "HR", q: "How does parental leave work?", a: "The handbook lists leave entitlements by role in its leave policy section.", src: "Employee-handbook.pdf · p. 14" },
  { name: "Product Docs", q: "How do I authenticate API requests?", a: "Send your API key in the Authorization header of each request.", src: "API-reference.pdf · p. 2" },
  { name: "Education", q: "When is the first assignment due?", a: "The syllabus lists every assignment deadline in the course schedule.", src: "Syllabus.pdf · p. 3" },
  { name: "Legal", q: "What does the contract say about termination?", a: "The termination clause explains the notice period and the conditions.", src: "Service-agreement.pdf · p. 9" },
  { name: "Healthcare", q: "What should I bring to my first appointment?", a: "The patient guide lists the documents and information to bring.", src: "Patient-guide.pdf · p. 2" },
];

export default function UseCases() {
  const root = useRef<HTMLElement>(null);
  const [active, setActive] = useState(0);
  const current = cases[active];

  useGSAP(
    () => {
      gsap.fromTo(
        ".uc-card",
        { opacity: 0, y: 16 },
        { opacity: 1, y: 0, duration: 0.45, ease: "power3.out" }
      );
    },
    { scope: root, dependencies: [active], revertOnUpdate: true }
  );

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(prefers-reduced-motion: no-preference)", () => {
        gsap.from(".uc-head", {
          opacity: 0,
          y: 40,
          duration: 0.9,
          ease: "power3.out",
          scrollTrigger: { trigger: ".uc-head", start: "top 85%" },
        });
        gsap.from(".uc-row", {
          opacity: 0,
          x: -30,
          duration: 0.7,
          stagger: 0.08,
          ease: "power3.out",
          scrollTrigger: { trigger: ".uc-list", start: "top 80%" },
        });
      });
      return () => mm.revert();
    },
    { scope: root }
  );

  return (
    <section id="use-cases" ref={root} className="mx-auto w-full max-w-[1440px] px-6 py-32 md:px-8">
      <div className="uc-head">
        <p className="font-mono text-sm tracking-widest text-secondary">USE CASES</p>
        <h2 className="font-display mt-4 text-[clamp(2.25rem,5vw,4.5rem)] font-bold leading-none tracking-tight">
          One platform, <span className="gradient-text">any knowledge base.</span>
        </h2>
      </div>

      <div className="mt-14 grid items-start gap-10 lg:grid-cols-2">
        <ul className="uc-list">
          {cases.map((c, i) => (
            <li key={c.name} className="uc-row border-b border-border first:border-t">
              <button
                onMouseEnter={() => setActive(i)}
                onFocus={() => setActive(i)}
                onClick={() => setActive(i)}
                aria-pressed={active === i}
                className="group flex w-full items-center justify-between py-6 text-left"
              >
                <span
                  className={`font-display text-3xl font-semibold tracking-tight transition-all duration-300 md:text-4xl ${
                    active === i ? "translate-x-3 text-foreground" : "text-muted group-hover:text-foreground"
                  }`}
                >
                  {c.name}
                </span>
                <ArrowUpRight
                  size={24}
                  className={`transition-all duration-300 ${active === i ? "text-primary opacity-100" : "opacity-0"}`}
                />
              </button>
            </li>
          ))}
        </ul>

        <div className="rounded-3xl border border-border bg-surface p-6 md:p-8 lg:sticky lg:top-28">
          <div className="uc-card">
            <p className="font-mono text-xs text-muted">ILLUSTRATIVE EXAMPLE, NOT REAL DATA</p>
            <div className="mt-6 space-y-3 text-sm">
              <div
                className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-tr-sm bg-primary px-4 py-3 text-primary-foreground"
              >
                {current.q}
              </div>
              <div className="max-w-[90%] rounded-2xl rounded-tl-sm bg-foreground/10 px-4 py-3">
                <p>{current.a}</p>
                <span className="mt-3 inline-block rounded-full border border-border px-2.5 py-1 font-mono text-[10px] text-muted">
                  {current.src}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}