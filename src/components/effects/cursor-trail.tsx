"use client";

import { useEffect, useRef } from "react";

type Rgb = [number, number, number];

const MAX_POINTS = 48; // length of the tail
const TAIL_WIDTH = 16; // thickness of the tail near the head
const DOT_RADIUS = 5;
const DOT_RADIUS_HOVER = 11; // dot size over links and buttons
const HEAD_FOLLOW = 22; // higher = tail head follows the cursor tighter

function hexToRgb(hex: string): Rgb {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim());
  if (!m) return [129, 140, 248];
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

export default function CursorTrail() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;
    const ctx = context;

    const enabled =
      window.matchMedia("(pointer: fine)").matches &&
      !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!enabled) return;

    // Keep native cursor for responsive feel while displaying trailing aura
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const resize = () => {
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener("resize", resize);

    let from: Rgb = [129, 140, 248];
    let to: Rgb = [34, 211, 238];
    const readColors = () => {
      const s = getComputedStyle(document.documentElement);
      from = hexToRgb(s.getPropertyValue("--primary"));
      to = hexToRgb(s.getPropertyValue("--secondary"));
    };
    readColors();
    const observer = new MutationObserver(readColors);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

    const pts: { x: number; y: number }[] = [];
    const pointer = { x: -100, y: -100, visible: false, hover: false };
    const head = { x: -100, y: -100 };
    let dotR = DOT_RADIUS;
    let raf = 0;
    let running = false;
    let seen = false;
    let last = 0;

    const mix = (t: number) =>
      `${Math.round(from[0] + (to[0] - from[0]) * t)},${Math.round(from[1] + (to[1] - from[1]) * t)},${Math.round(from[2] + (to[2] - from[2]) * t)}`;

    function draw() {
      ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);

      const n = pts.length;
      if (n >= 2) {
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        for (let i = 1; i < n; i++) {
          const t = i / (n - 1);
          const rgb = mix(t);
          const w = 2 + t * TAIL_WIDTH;
          const a = 0.12 + t * 0.85;
          ctx.beginPath();
          ctx.moveTo(pts[i - 1].x, pts[i - 1].y);
          ctx.lineTo(pts[i].x, pts[i].y);
          ctx.strokeStyle = `rgba(${rgb},${a * 0.1})`;
          ctx.lineWidth = w * 2.8;
          ctx.stroke();
          ctx.strokeStyle = `rgba(${rgb},${a * 0.22})`;
          ctx.lineWidth = w * 1.7;
          ctx.stroke();
          ctx.strokeStyle = `rgba(${rgb},${a})`;
          ctx.lineWidth = w;
          ctx.stroke();
        }
      }

      if (pointer.visible) {
        const rgb = mix(1);
        ctx.fillStyle = `rgba(${rgb},0.16)`;
        ctx.beginPath();
        ctx.arc(pointer.x, pointer.y, dotR * 2.6, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = `rgba(${rgb},0.35)`;
        ctx.beginPath();
        ctx.arc(pointer.x, pointer.y, dotR * 1.6, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = `rgb(${rgb})`;
        ctx.beginPath();
        ctx.arc(pointer.x, pointer.y, dotR, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = "rgba(255,255,255,0.95)";
        ctx.beginPath();
        ctx.arc(pointer.x, pointer.y, dotR * 0.4, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    function frame(now: number) {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;

      const k = 1 - Math.exp(-dt * HEAD_FOLLOW);
      head.x += (pointer.x - head.x) * k;
      head.y += (pointer.y - head.y) * k;
      const moving = Math.hypot(pointer.x - head.x, pointer.y - head.y) > 0.5;

      if (moving) {
        pts.push({ x: head.x, y: head.y });
        if (pts.length > MAX_POINTS) pts.shift();
      } else if (pts.length > 0) {
        pts.shift();
      }

      const targetR = pointer.hover ? DOT_RADIUS_HOVER : DOT_RADIUS;
      dotR += (targetR - dotR) * (1 - Math.exp(-dt * 14));

      draw();

      const settling = Math.abs(targetR - dotR) > 0.05;
      if (moving || pts.length > 1 || settling) {
        raf = requestAnimationFrame(frame);
      } else {
        running = false;
      }
    }

    const start = () => {
      if (running) return;
      running = true;
      last = performance.now();
      raf = requestAnimationFrame(frame);
    };

    const onMove = (e: PointerEvent) => {
      if (e.pointerType === "touch") return;
      pointer.x = e.clientX;
      pointer.y = e.clientY;
      pointer.visible = true;
      const el = e.target as Element | null;
      pointer.hover = !!el?.closest?.("a,button,[role='button'],input,textarea,select,label,summary");
      if (!seen) {
        head.x = pointer.x;
        head.y = pointer.y;
        seen = true;
      }
      start();
    };
    const onLeave = () => {
      pointer.visible = false;
      start();
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    document.documentElement.addEventListener("mouseleave", onLeave);
    window.addEventListener("blur", onLeave);

    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("resize", resize);
      document.documentElement.removeEventListener("mouseleave", onLeave);
      window.removeEventListener("blur", onLeave);
    };
  }, []);

  return <canvas ref={ref} aria-hidden="true" className="pointer-events-none fixed inset-0 z-[120] h-full w-full" />;
}