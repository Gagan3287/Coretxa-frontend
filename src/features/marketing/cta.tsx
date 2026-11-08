"use client";

import { useRef } from "react";
import Link from "next/link";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(useGSAP, ScrollTrigger);

export default function Cta() {
  const root = useRef<HTMLElement>(null);
  const button = useRef<HTMLAnchorElement>(null);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();

      mm.add("(prefers-reduced-motion: no-preference)", () => {
        gsap.from(".cta-inner", {
          opacity: 0,
          y: 60,
          duration: 1,
          ease: "power3.out",
          scrollTrigger: { trigger: root.current, start: "top 75%" },
        });
      });

      mm.add("(pointer: fine) and (prefers-reduced-motion: no-preference)", () => {
        const el = button.current!;
        const x = gsap.quickTo(el, "x", { duration: 0.5, ease: "power3" });
        const y = gsap.quickTo(el, "y", { duration: 0.5, ease: "power3" });
        const move = (e: PointerEvent) => {
          const r = el.getBoundingClientRect();
          x((e.clientX - (r.left + r.width / 2)) * 0.3);
          y((e.clientY - (r.top + r.height / 2)) * 0.3);
        };
        const leave = () => {
          x(0);
          y(0);
        };
        el.addEventListener("pointermove", move);
        el.addEventListener("pointerleave", leave);
        return () => {
          el.removeEventListener("pointermove", move);
          el.removeEventListener("pointerleave", leave);
        };
      });

      return () => mm.revert();
    },
    { scope: root }
  );

  return (
    <section ref={root} className="px-6 pb-32 md:px-8">
      <div
        className="cta-inner relative mx-auto max-w-[1440px] overflow-hidden rounded-[2rem] border border-border px-8 py-20 text-center md:py-28"
        style={{
          background:
            "radial-gradient(60% 80% at 50% 0%, color-mix(in srgb, var(--primary) 28%, transparent), transparent), var(--surface)",
        }}
      >
        <h2 className="font-display mx-auto max-w-3xl text-[clamp(2.25rem,5.5vw,5rem)] font-bold leading-[1.02] tracking-tight">
          Ready to ask your docs <span className="gradient-text">anything?</span>
        </h2>
        <p className="mx-auto mt-6 max-w-xl text-muted">
          Build your first assistant, brand it and put it on your website.
        </p>
        <Link
          ref={button}
          href="/dashboard"
          className="mt-10 inline-flex rounded-full bg-primary px-10 py-5 text-sm font-semibold text-primary-foreground"
        >
          Start building
        </Link>
      </div>
    </section>
  );
}