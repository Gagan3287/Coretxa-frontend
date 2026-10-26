"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";

// Frosted glass circles: one trails the cursor, the others drift on their own.
const ORBS = [
  { size: 170, ax: 0.5, ay: 0.5, follow: 0.07, drift: 0, phase: 0 },
  { size: 110, ax: 0.78, ay: 0.2, follow: 0, drift: 1, phase: 1.7 },
  { size: 280, ax: 0.9, ay: 0.95, follow: 0, drift: 1, phase: 3.1 },
];

export default function GlassOrbs() {
  const refs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    if (!window.matchMedia("(pointer: fine)").matches) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const pointer = { x: window.innerWidth * 0.5, y: window.innerHeight * 0.5 };
    const pos = ORBS.map((o) => ({ x: window.innerWidth * o.ax, y: window.innerHeight * o.ay }));

    const onMove = (e: PointerEvent) => {
      pointer.x = e.clientX;
      pointer.y = e.clientY;
    };
    window.addEventListener("pointermove", onMove, { passive: true });

    const tick = (time: number) => {
      const t = time / 1000;
      ORBS.forEach((o, i) => {
        const el = refs.current[i];
        if (!el) return;
        let tx: number;
        let ty: number;
        if (o.follow) {
          tx = pointer.x + 70;
          ty = pointer.y + 70;
        } else {
          tx = window.innerWidth * o.ax + Math.sin(t * 0.3 + o.phase) * 34;
          ty = window.innerHeight * o.ay + Math.cos(t * 0.24 + o.phase) * 26;
          const dx = pointer.x - tx;
          const dy = pointer.y - ty;
          const d = Math.hypot(dx, dy);
          if (d < 320 && d > 1) {
            const pull = (1 - d / 320) * 40;
            tx += (dx / d) * pull;
            ty += (dy / d) * pull;
          }
        }
        const k = o.follow || 0.04;
        pos[i].x += (tx - pos[i].x) * k;
        pos[i].y += (ty - pos[i].y) * k;
        el.style.transform = `translate3d(${pos[i].x - o.size / 2}px, ${pos[i].y - o.size / 2}px, 0)`;
      });
    };
    gsap.ticker.add(tick);

    return () => {
      gsap.ticker.remove(tick);
      window.removeEventListener("pointermove", onMove);
    };
  }, []);

  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-30 hidden overflow-hidden [@media(pointer:fine)]:block">
      {ORBS.map((o, i) => (
        <div
          key={i}
          ref={(el) => {
            refs.current[i] = el;
          }}
          className="absolute left-0 top-0 rounded-full border border-foreground/20 backdrop-blur-[2px]"
          style={{
            width: o.size,
            height: o.size,
            background:
              "radial-gradient(circle at 30% 26%, rgba(255,255,255,0.22), rgba(255,255,255,0.04) 45%, transparent 70%)",
            boxShadow: "inset 0 0 30px rgba(255,255,255,0.07), 0 0 50px rgba(34,211,238,0.12)",
          }}
        />
      ))}
    </div>
  );
}