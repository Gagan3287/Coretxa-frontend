"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import HeroChat from "@/features/marketing/hero-chat";

/** The chat card floating in 3D layers. It tilts toward the cursor. */
export default function TiltDevice() {
  const wrap = useRef<HTMLDivElement>(null);
  const tilt = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const wrapEl = wrap.current;
    const tiltEl = tilt.current;
    if (!wrapEl || !tiltEl) return;
    if (!window.matchMedia("(pointer: fine)").matches) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const rx = gsap.quickTo(tiltEl, "rotationX", { duration: 0.8, ease: "power3" });
    const ry = gsap.quickTo(tiltEl, "rotationY", { duration: 0.8, ease: "power3" });

    const onMove = (e: PointerEvent) => {
      const r = wrapEl.getBoundingClientRect();
      const nx = ((e.clientX - (r.left + r.width / 2)) / r.width) * 2;
      const ny = ((e.clientY - (r.top + r.height / 2)) / r.height) * 2;
      ry(Math.max(-1, Math.min(1, nx)) * 16);
      rx(Math.max(-1, Math.min(1, ny)) * -12);
    };
    const onLeave = () => {
      rx(0);
      ry(0);
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    document.documentElement.addEventListener("mouseleave", onLeave);
    return () => {
      window.removeEventListener("pointermove", onMove);
      document.documentElement.removeEventListener("mouseleave", onLeave);
    };
  }, []);

  return (
    <div ref={wrap} className="auth-visual grid h-full w-full place-items-center [perspective:1200px]">
      <div ref={tilt} className="relative [transform-style:preserve-3d]">
        <div
          aria-hidden="true"
          className="absolute -inset-[10%] rounded-[2rem] border border-primary/30 bg-primary/5"
          style={{ transform: "translateZ(-90px)" }}
        />
        <div
          aria-hidden="true"
          className="absolute -inset-[22%] rounded-[2.5rem] border border-secondary/20"
          style={{ transform: "translateZ(-200px)" }}
        />
        <HeroChat />
        <span
          aria-hidden="true"
          className="absolute -right-8 top-10 rounded-full border border-secondary/40 bg-surface px-4 py-2 font-mono text-xs text-secondary shadow-xl"
          style={{ transform: "translateZ(90px)" }}
        >
          PDF READY ✓
        </span>
        <span
          aria-hidden="true"
          className="absolute -left-10 bottom-14 rounded-full border border-primary/40 bg-surface px-4 py-2 font-mono text-xs text-primary shadow-xl"
          style={{ transform: "translateZ(120px)" }}
        >
          SOURCE · P.2
        </span>
      </div>
    </div>
  );
}