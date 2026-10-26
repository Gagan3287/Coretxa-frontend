"use client";

import { useRef } from "react";
import Link from "next/link";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import GlassOrbs from "@/components/effects/glass-orbs";
import ParticleNetwork from "@/components/effects/particle-network";
import ScrambleText from "@/components/effects/scramble-text";
import { anton } from "@/lib/fonts";
import { whenIntroDone } from "@/lib/utils/intro-gate";
import TiltDevice from "./tilt-device";

gsap.registerPlugin(useGSAP);

interface Props {
  tagline: string[];
  description: string;
  children: React.ReactNode;
}

export default function AuthShell({ tagline, description, children }: Props) {
  const root = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(prefers-reduced-motion: no-preference)", () => {
        const tl = gsap.timeline({ paused: true, defaults: { ease: "power3.out" } });
        tl.from(".auth-visual", { opacity: 0, x: -40, duration: 1 }, 0)
          .from(".auth-tagline", { opacity: 0, y: 40, duration: 0.9 }, 0.15)
          .from(".auth-reveal", { opacity: 0, y: 28, duration: 0.7, stagger: 0.08 }, 0.1);
        return whenIntroDone(() => tl.play());
      });
      return () => mm.revert();
    },
    { scope: root }
  );

  return (
    <div ref={root} className="relative min-h-screen overflow-hidden bg-background text-foreground">
      <ParticleNetwork
        className="absolute inset-0 h-full w-full"
        density={0.45}
        linkDistance={130}
        mouseRadius={170}
        mouseStrength={1}
        speed={12}
      />
      <GlassOrbs />

      <Link
        href="/"
        className="absolute left-6 top-8 z-20 font-mono text-xs tracking-[0.18em] text-muted transition hover:text-secondary md:left-12"
      >
        <ScrambleText text="← RETURN TO BASE" />
      </Link>

      <div className="relative z-10 grid min-h-screen lg:grid-cols-2">
        <section className="relative hidden flex-col border-r border-border px-12 pb-12 pt-28 lg:flex">
          <div className="grid flex-1 place-items-center">
            <TiltDevice />
          </div>
          <div className="auth-tagline">
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">{"// CORTEXA"}</p>
            <h2
              className={`${anton.className} mt-4 text-[clamp(3rem,5.2vw,5.5rem)] uppercase leading-[0.92] tracking-[0.01em]`}
            >
              {tagline.map((line, i) => (
                <span key={line} className="block">
                  <span
                    className={`inline-block cursor-default transition-all duration-300 hover:text-secondary hover:[text-shadow:0_0_32px_var(--secondary)] ${
                      i === tagline.length - 1 ? "gradient-text" : ""
                    }`}
                  >
                    {line}
                  </span>
                </span>
              ))}
            </h2>
            <p className="mt-5 max-w-md text-sm text-muted">{description}</p>
          </div>
        </section>

        <section className="flex items-center justify-center px-6 py-28 md:px-12 lg:py-16">
          <div className="w-full max-w-[520px]">{children}</div>
        </section>
      </div>
    </div>
  );
}