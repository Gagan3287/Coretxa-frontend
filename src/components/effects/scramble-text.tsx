"use client";

import { useEffect, useRef, useState } from "react";

const GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#$%&*+<>/";

/** Text that scrambles into place when hovered or focused. */
export default function ScrambleText({ text }: { text: string }) {
  const [out, setOut] = useState(text);
  const raf = useRef(0);

  useEffect(() => () => cancelAnimationFrame(raf.current), []);

  const run = () => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    cancelAnimationFrame(raf.current);
    const start = performance.now();
    const duration = 550;
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const solved = Math.floor(t * text.length);
      setOut(
        Array.from(text)
          .map((ch, i) =>
            i < solved || ch === " " ? ch : GLYPHS[Math.floor(Math.random() * GLYPHS.length)]
          )
          .join("")
      );
      if (t < 1) raf.current = requestAnimationFrame(step);
      else setOut(text);
    };
    raf.current = requestAnimationFrame(step);
  };

  return (
    <span onMouseEnter={run} onFocus={run}>
      <span className="sr-only">{text}</span>
      <span aria-hidden="true">{out}</span>
    </span>
  );
}