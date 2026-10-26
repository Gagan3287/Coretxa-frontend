"use client";

import { useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";
import { FileSearch, Palette, Quote, Rocket } from "lucide-react";

gsap.registerPlugin(useGSAP, ScrollTrigger);

const features = [
  { icon: FileSearch, title: "Answers from your documents", text: "The assistant answers using the documents you upload." },
  { icon: Quote, title: "Sources you can check", text: "Answers can point back to the document they came from." },
  { icon: Palette, title: "Your brand, your chat", text: "Set the name, color, greeting and position of the widget." },
  { icon: Rocket, title: "Deploy anywhere", text: "Use a script, an iframe or a hosted page, with guides for popular platforms." },
];

export default function Features() {
  const root = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      const q = gsap.utils.selector(root);
      const mm = gsap.matchMedia();
      mm.add("(prefers-reduced-motion: no-preference)", () => {
        gsap.set(q(".feat-card"), { opacity: 0, y: 50 });
        ScrollTrigger.batch(q(".feat-card"), {
          start: "top 88%",
          onEnter: (els) =>
            gsap.to(els, { opacity: 1, y: 0, duration: 0.8, stagger: 0.12, ease: "power3.out", overwrite: true }),
        });
      });
      return () => mm.revert();
    },
    { scope: root }
  );

  return (
    <section id="features" ref={root} className="border-t border-border bg-surface/40 py-32">
      <div className="mx-auto w-full max-w-[1440px] px-6 md:px-8">
        <p className="font-mono text-sm tracking-widest text-secondary">FEATURES</p>
        <h2 className="font-display mt-4 text-[clamp(2.25rem,5vw,4.5rem)] font-bold leading-none tracking-tight">
          Everything to <span className="gradient-text">go live.</span>
        </h2>
        <div className="mt-14 grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
          {features.map(({ icon: Icon, title, text }) => (
            <div
              key={title}
              className="feat-card rounded-3xl border border-border bg-surface p-7 transition-colors duration-300 hover:border-primary/50"
            >
              <div className="grid h-12 w-12 place-items-center rounded-2xl bg-primary/15 text-primary">
                <Icon size={22} />
              </div>
              <h3 className="font-display mt-6 text-xl font-bold">{title}</h3>
              <p className="mt-3 text-sm text-muted">{text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}