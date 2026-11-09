"use client";

import { useRef } from "react";
import Link from "next/link";
import { Download } from "lucide-react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import ParticleNetwork from "@/components/effects/particle-network";
import HeroChat from "./hero-chat";
import Headline from "./headline";

gsap.registerPlugin(useGSAP);

export default function Hero() {
  const root = useRef<HTMLElement>(null);
  const glow = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const section = root.current!;
      const glowEl = glow.current!;
      const rect = section.getBoundingClientRect();
      gsap.set(glowEl, { x: rect.width * 0.6 - 250, y: rect.height * 0.25 - 250 });

      const mm = gsap.matchMedia();
      const introPlaying = document.documentElement.dataset.intro === "playing";

      mm.add("(prefers-reduced-motion: no-preference)", () => {
        gsap.set(".line-mask", { overflow: "hidden" });
        const tl = gsap.timeline({
          paused: introPlaying,
          defaults: { ease: "power4.out" },
          onComplete: () => {
            gsap.set(".line-mask", { overflow: "visible" });
          },
        });
        tl.from(".hero-eyebrow", { opacity: 0, y: 20, duration: 0.8 })
          .from(".line-inner", { yPercent: 110, duration: 1.1, stagger: 0.14 }, "-=0.5")
          .from(".hero-sub", { opacity: 0, y: 20, duration: 0.8 }, "-=0.6")
          .from(".hero-cta", { opacity: 0, y: 24, duration: 0.8, stagger: 0.1 }, "-=0.6")
          .from(".hero-visual", { opacity: 0, scale: 0.94, y: 30, duration: 1.2 }, "-=1");

        if (!introPlaying) return;
        const go = () => {
          tl.play();
        };
        window.addEventListener("cortexa:intro-done", go, { once: true });
        return () => window.removeEventListener("cortexa:intro-done", go);
      });

      mm.add("(pointer: fine) and (prefers-reduced-motion: no-preference)", () => {
        const x = gsap.quickTo(glowEl, "x", { duration: 0.8, ease: "power3" });
        const y = gsap.quickTo(glowEl, "y", { duration: 0.8, ease: "power3" });
        const move = (e: PointerEvent) => {
          const r = section.getBoundingClientRect();
          x(e.clientX - r.left - 250);
          y(e.clientY - r.top - 250);
        };
        section.addEventListener("pointermove", move);
        return () => section.removeEventListener("pointermove", move);
      });

      return () => mm.revert();
    },
    { scope: root }
  );

  return (
    <section ref={root} className="relative overflow-hidden pt-24">
      <div
        ref={glow}
        className="pointer-events-none absolute left-0 top-0 h-[500px] w-[500px] rounded-full opacity-30 blur-3xl"
        style={{ background: "radial-gradient(circle, var(--primary), transparent 65%)" }}
        aria-hidden="true"
      />

      <ParticleNetwork
        className="absolute inset-0 h-full w-full"
        density={0.55}
        linkDistance={140}
        mouseRadius={190}
        mouseStrength={1}
        speed={14}
      />

      <div className="relative flex w-full flex-col justify-center px-6 pb-16 pt-10 md:px-12 lg:min-h-[calc(100vh-6rem)]">
        <div className="grid items-center gap-12 xl:grid-cols-[1fr_auto] xl:gap-10">
          <div>
            <p className="hero-eyebrow mb-6 font-mono text-sm tracking-widest text-secondary">
              {"// AI CHATBOTS FOR YOUR DOCUMENTS"}
            </p>

            <Headline />

            <p className="hero-sub mt-10 max-w-xl text-lg text-muted">
              Upload your documents, brand the chat, and add it to any website. Answers come from your own
              content, with sources.
            </p>
            <div className="mt-8 flex flex-wrap gap-4">
              <Link
                href="/login"
                className="hero-cta rounded-full bg-primary px-8 py-4 text-sm font-semibold text-primary-foreground transition-transform hover:-translate-y-1"
              >
                Start building
              </Link>
              <a
                href="https://github.com/Gagan3287/Coretxa-frontend/releases"
                target="_blank"
                rel="noopener noreferrer"
                className="hero-cta inline-flex items-center gap-2 rounded-full border border-secondary/40 bg-secondary/10 px-6 py-4 text-sm font-semibold text-secondary transition-transform hover:-translate-y-1 hover:border-secondary hover:bg-secondary/20"
              >
                <Download size={16} />
                Download App (.exe)
              </a>
              <a
                href="#how"
                className="hero-cta rounded-full border border-border bg-surface px-8 py-4 text-sm font-semibold transition-transform hover:-translate-y-1"
              >
                See how it works
              </a>
            </div>
          </div>

          <div className="hero-visual flex w-full justify-start xl:w-auto xl:justify-end">
            <HeroChat />
          </div>
        </div>
      </div>
    </section>
  );
}