"use client";

import { useEffect, useRef } from "react";
import { anton } from "@/lib/fonts";
import { clawMaskUrl } from "./claw";
import "./headline.css";

type Word = { text: string; glow: "a" | "b"; deploy?: boolean };

const lines: Word[][] = [
  [
    { text: "Push", glow: "a" },
    { text: "Docs", glow: "b" },
  ],
  [
    { text: "Customize", glow: "a" },
    { text: "&", glow: "b" },
    { text: "Deploy", glow: "a", deploy: true },
  ],
  [
    { text: "Chatbots", glow: "b" },
    { text: "Instantly", glow: "a" },
  ],
];

const CLAW = clawMaskUrl();

const RADIUS = 150; // px: how far from the cursor letters start to light up
const SMOOTH = 10; // higher = snappier glow response

export default function Headline() {
  const root = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    const el = root.current;
    if (!el) return;
    if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const words = Array.from(el.querySelectorAll<HTMLElement>("[data-word]"));
    const letters = words.map((w) => Array.from(w.querySelectorAll<HTMLElement>("[data-letter]")));
    const level = letters.map((ls) => ls.map(() => 0));
    const pointer = { x: -9999, y: -9999, active: false };
    let visible = false;
    let running = false;
    let raf = 0;
    let last = 0;

    const frame = (now: number) => {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      const k = 1 - Math.exp(-dt * SMOOTH);

      const hr = el.getBoundingClientRect();
      const near =
        pointer.active &&
        pointer.x > hr.left - RADIUS &&
        pointer.x < hr.right + RADIUS &&
        pointer.y > hr.top - RADIUS &&
        pointer.y < hr.bottom + RADIUS;

      const wordRects = near ? words.map((w) => w.getBoundingClientRect()) : [];
      const letterRects = near ? letters.map((ls) => ls.map((l) => l.getBoundingClientRect())) : [];

      let busy = false;
      for (let wi = 0; wi < words.length; wi++) {
        let inside = false;
        if (near) {
          const r = wordRects[wi];
          inside =
            pointer.x >= r.left - 6 &&
            pointer.x <= r.right + 6 &&
            pointer.y >= r.top - 4 &&
            pointer.y <= r.bottom + 4;
        }
        for (let li = 0; li < letters[wi].length; li++) {
          let target = 0;
          if (near) {
            const r = letterRects[wi][li];
            const d = Math.hypot(pointer.x - (r.left + r.width / 2), pointer.y - (r.top + r.height / 2));
            target = Math.pow(Math.max(0, 1 - d / RADIUS), 1.6);
            if (inside) target = 1;
          }
          const cur = level[wi][li];
          let next = cur + (target - cur) * k;
          if (target === 0 && next < 0.004) next = 0;
          if (next !== cur) {
            level[wi][li] = next;
            letters[wi][li].style.setProperty("--p", next.toFixed(3));
          }
          if (next > 0 || target > 0) busy = true;
        }
      }

      if (busy && visible) raf = requestAnimationFrame(frame);
      else running = false;
    };

    const start = () => {
      if (running || !visible) return;
      running = true;
      last = performance.now();
      raf = requestAnimationFrame(frame);
    };

    const onMove = (e: PointerEvent) => {
      if (e.pointerType === "touch") return;
      pointer.x = e.clientX;
      pointer.y = e.clientY;
      pointer.active = true;
      start();
    };
    const onLeave = () => {
      pointer.active = false;
      start();
    };

    const io = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (visible) start();
      else {
        cancelAnimationFrame(raf);
        running = false;
      }
    });
    io.observe(el);

    window.addEventListener("pointermove", onMove, { passive: true });
    document.documentElement.addEventListener("mouseleave", onLeave);
    window.addEventListener("blur", onLeave);

    return () => {
      cancelAnimationFrame(raf);
      io.disconnect();
      window.removeEventListener("pointermove", onMove);
      document.documentElement.removeEventListener("mouseleave", onLeave);
      window.removeEventListener("blur", onLeave);
    };
  }, []);

  return (
    <h1
      ref={root}
      className={`${anton.className} text-[clamp(2.5rem,10.5vw,7rem)] uppercase leading-[0.92] tracking-[0.01em] xl:text-[clamp(4rem,7vw,8.5rem)]`}
    >
      {lines.map((words, li) => (
        <span key={li} className="line-mask block py-[0.03em]">
          <span className="line-inner flex flex-wrap gap-x-[0.22em]">
            {words.map((w) => {
              const chars = Array.from(w.text);
              return (
                <span
                  key={w.text}
                  data-word
                  className={w.deploy ? "hl-word hl-deploy" : "hl-word"}
                  style={
                    {
                      "--glow": w.glow === "b" ? "var(--primary)" : "var(--secondary)",
                      ...(w.deploy
                        ? {
                            WebkitMaskImage: CLAW,
                            maskImage: CLAW,
                            WebkitMaskSize: "100% 100%",
                            maskSize: "100% 100%",
                            WebkitMaskRepeat: "no-repeat",
                            maskRepeat: "no-repeat",
                          }
                        : {}),
                    } as React.CSSProperties
                  }
                >
                  <span className="sr-only">{w.text} </span>
                  <span aria-hidden="true" className="hl-chars">
                    {chars.map((c, i) => (
                      <span
                        key={i}
                        data-letter
                        data-c={c}
                        className="hl-letter"
                        style={{ "--i": i, "--n": chars.length } as React.CSSProperties}
                      >
                        {c}
                      </span>
                    ))}
                  </span>
                </span>
              );
            })}
          </span>
        </span>
      ))}
    </h1>
  );
}