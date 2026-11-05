"use client";

import { useEffect, useRef } from "react";

interface Bubble {
  id: number;
  x: number;
  y: number;
  radius: number;
  vx: number;
  vy: number;
  wobbleSpeed: number;
  wobbleAmp: number;
  wobblePhase: number;
  hue: number;
  alpha: number;
}

interface SlicedHalf {
  id: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  rotation: number;
  rotSpeed: number;
  hue: number;
  alpha: number;
  side: "top" | "bottom";
}

interface SliceSpark {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  alpha: number;
  hue: number;
}

const MAX_BUBBLES = 20;
const HUES = [186, 198, 215, 265, 280]; // Cyan, electric blue, violet, purple
const SWIPE_SPEED_THRESHOLD = 600; // px/sec minimum for a fast swipe

function createBubble(x: number, y: number, radius?: number): Bubble {
  const r = radius ?? Math.floor(26 + Math.random() * 32);
  const hue = HUES[Math.floor(Math.random() * HUES.length)];
  return {
    id: Math.random(),
    x,
    y,
    radius: r,
    vx: (Math.random() - 0.5) * 0.4,
    vy: -(0.5 + Math.random() * 0.8),
    wobbleSpeed: 0.015 + Math.random() * 0.02,
    wobbleAmp: 0.4 + Math.random() * 0.6,
    wobblePhase: Math.random() * Math.PI * 2,
    hue,
    alpha: 0.35 + Math.random() * 0.3,
  };
}

export default function BubbleCanvas({ className = "" }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const bubblesRef = useRef<Bubble[]>([]);
  const halvesRef = useRef<SlicedHalf[]>([]);
  const sparksRef = useRef<SliceSpark[]>([]);
  const isVisibleRef = useRef(true);
  const animFrameRef = useRef<number | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    let width = 0;
    let height = 0;
    let dpr = 1;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      dpr = Math.min(window.devicePixelRatio || 1, 2);

      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      // Initialize initial ambient bubbles if empty
      if (bubblesRef.current.length === 0 && width > 0 && height > 0) {
        const count = reducedMotion ? 8 : 11;
        const initial: Bubble[] = [];
        for (let i = 0; i < count; i++) {
          const bx = Math.random() * width;
          const by = Math.random() * height;
          initial.push(createBubble(bx, by));
        }
        bubblesRef.current = initial;
      }
    };

    resize();
    const ro = new ResizeObserver(() => resize());
    ro.observe(canvas);

    // If reduced motion, render static background once
    if (reducedMotion) {
      const drawStatic = () => {
        ctx.clearRect(0, 0, width, height);
        for (const b of bubblesRef.current) {
          ctx.save();
          ctx.beginPath();
          ctx.arc(b.x, b.y, b.radius, 0, Math.PI * 2);
          const grad = ctx.createRadialGradient(
            b.x - b.radius * 0.3,
            b.y - b.radius * 0.3,
            b.radius * 0.1,
            b.x,
            b.y,
            b.radius
          );
          grad.addColorStop(0, `hsla(${b.hue}, 90%, 80%, ${b.alpha * 0.8})`);
          grad.addColorStop(0.6, `hsla(${b.hue}, 80%, 60%, ${b.alpha * 0.3})`);
          grad.addColorStop(1, `hsla(${b.hue}, 85%, 65%, ${b.alpha * 0.6})`);
          ctx.fillStyle = grad;
          ctx.fill();

          ctx.beginPath();
          ctx.arc(b.x, b.y, b.radius, 0, Math.PI * 2);
          ctx.strokeStyle = `hsla(${b.hue}, 90%, 75%, ${b.alpha * 0.7})`;
          ctx.lineWidth = 1;
          ctx.stroke();
          ctx.restore();
        }
      };
      drawStatic();
      return () => {
        ro.disconnect();
      };
    }

    // Slicing logic: slices bubble into two halves that drift apart along normal and fade
    const sliceBubble = (b: Bubble, dx: number, dy: number) => {
      const sliceAngle = Math.atan2(dy, dx);
      const normalAngle = sliceAngle + Math.PI / 2;
      const driftSpeed = 2.4;

      halvesRef.current.push({
        id: Math.random(),
        x: b.x + Math.cos(normalAngle) * 5,
        y: b.y + Math.sin(normalAngle) * 5,
        vx: Math.cos(normalAngle) * driftSpeed + b.vx * 0.3,
        vy: Math.sin(normalAngle) * driftSpeed + b.vy * 0.3,
        radius: b.radius,
        rotation: sliceAngle,
        rotSpeed: 0.025 + Math.random() * 0.02,
        hue: b.hue,
        alpha: b.alpha,
        side: "top",
      });

      halvesRef.current.push({
        id: Math.random(),
        x: b.x - Math.cos(normalAngle) * 5,
        y: b.y - Math.sin(normalAngle) * 5,
        vx: -Math.cos(normalAngle) * driftSpeed + b.vx * 0.3,
        vy: -Math.sin(normalAngle) * driftSpeed + b.vy * 0.3,
        radius: b.radius,
        rotation: sliceAngle,
        rotSpeed: -(0.025 + Math.random() * 0.02),
        hue: b.hue,
        alpha: b.alpha,
        side: "bottom",
      });

      // Subtle severed droplets
      for (let i = -2; i <= 2; i++) {
        const offset = (i / 3) * (b.radius * 0.75);
        sparksRef.current.push({
          x: b.x + Math.cos(sliceAngle) * offset,
          y: b.y + Math.sin(sliceAngle) * offset,
          vx: (Math.random() - 0.5) * 1.5,
          vy: (Math.random() - 0.5) * 1.5,
          radius: 1.2 + Math.random() * 1.5,
          alpha: b.alpha * 0.9,
          hue: b.hue,
        });
      }
    };

    // Pointer tracking
    let lastPoint: { x: number; y: number; time: number } | null = null;
    let downPoint: { x: number; y: number; time: number } | null = null;
    let wasFastSwipe = false;

    const resetPointerState = () => {
      lastPoint = null;
      downPoint = null;
      wasFastSwipe = false;
    };

    const checkAndSliceBubbles = (x0: number, y0: number, x1: number, y1: number) => {
      const dx = x1 - x0;
      const dy = y1 - y0;
      const segLengthSq = dx * dx + dy * dy;
      if (segLengthSq === 0) return;

      const bubbles = bubblesRef.current;
      for (let i = bubbles.length - 1; i >= 0; i--) {
        const b = bubbles[i];
        // Project circle center onto swipe line segment
        const t = Math.max(0, Math.min(1, ((b.x - x0) * dx + (b.y - y0) * dy) / segLengthSq));
        const projX = x0 + t * dx;
        const projY = y0 + t * dy;
        const dist = Math.hypot(b.x - projX, b.y - projY);

        if (dist <= b.radius) {
          sliceBubble(b, dx, dy);
          bubbles.splice(i, 1);
        }
      }
    };

    const onPointerDown = (e: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const time = performance.now();
      downPoint = { x, y, time };
      lastPoint = { x, y, time };
      wasFastSwipe = false;
    };

    const onPointerMove = (e: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const time = performance.now();

      if (lastPoint) {
        const dt = (time - lastPoint.time) / 1000;
        const dx = x - lastPoint.x;
        const dy = y - lastPoint.y;
        const dist = Math.hypot(dx, dy);

        // Check velocity for fast swipe
        if (dt > 0.005 && dt < 0.25) {
          const speed = dist / dt;
          if (speed >= SWIPE_SPEED_THRESHOLD && dist >= 12) {
            wasFastSwipe = true;
            checkAndSliceBubbles(lastPoint.x, lastPoint.y, x, y);
          }
        }
      }

      lastPoint = { x, y, time };
    };

    const onPointerUp = (e: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      // Only click in empty space creates a bubble
      if (downPoint && !wasFastSwipe) {
        const moveDist = Math.hypot(x - downPoint.x, y - downPoint.y);
        if (moveDist < 8 && x >= 0 && x <= width && y >= 0 && y <= height) {
          const hitBubble = bubblesRef.current.some(
            (b) => Math.hypot(b.x - x, b.y - y) <= b.radius
          );
          if (!hitBubble) {
            if (bubblesRef.current.length >= MAX_BUBBLES) {
              bubblesRef.current.shift();
            }
            bubblesRef.current.push(createBubble(x, y));
          }
        }
      }

      resetPointerState();
    };

    const onPointerCancel = () => resetPointerState();
    const onPointerLeave = () => resetPointerState();
    const onWindowBlur = () => resetPointerState();

    canvas.addEventListener("pointerdown", onPointerDown);
    canvas.addEventListener("pointermove", onPointerMove);
    canvas.addEventListener("pointerup", onPointerUp);
    canvas.addEventListener("pointercancel", onPointerCancel);
    canvas.addEventListener("pointerleave", onPointerLeave);
    window.addEventListener("blur", onWindowBlur);

    // Render loop
    const render = () => {
      if (!isVisibleRef.current) {
        animFrameRef.current = requestAnimationFrame(render);
        return;
      }

      ctx.clearRect(0, 0, width, height);

      // 1. Render active floating bubbles
      const bubbles = bubblesRef.current;
      for (let i = bubbles.length - 1; i >= 0; i--) {
        const b = bubbles[i];

        // Float upwards with subtle organic wobble (NEVER tracks cursor)
        b.wobblePhase += b.wobbleSpeed;
        b.x += b.vx + Math.sin(b.wobblePhase) * b.wobbleAmp;
        b.y += b.vy;

        // Reset if floated above top
        if (b.y < -b.radius * 2) {
          b.y = height + b.radius + 10;
          b.x = Math.random() * width;
        }

        // Soft horizontal wrap
        if (b.x < -b.radius) b.x = width + b.radius;
        if (b.x > width + b.radius) b.x = -b.radius;

        // Draw glassy spherical bubble
        ctx.save();
        ctx.beginPath();
        ctx.arc(b.x, b.y, b.radius, 0, Math.PI * 2);

        const grad = ctx.createRadialGradient(
          b.x - b.radius * 0.3,
          b.y - b.radius * 0.3,
          b.radius * 0.08,
          b.x,
          b.y,
          b.radius
        );
        grad.addColorStop(0, `hsla(${b.hue}, 95%, 85%, ${b.alpha * 0.75})`);
        grad.addColorStop(0.5, `hsla(${b.hue}, 80%, 60%, ${b.alpha * 0.22})`);
        grad.addColorStop(0.85, `hsla(${b.hue}, 85%, 65%, ${b.alpha * 0.45})`);
        grad.addColorStop(1, `hsla(${b.hue}, 90%, 75%, ${b.alpha * 0.7})`);
        ctx.fillStyle = grad;
        ctx.fill();

        // Delicate perimeter glow
        ctx.beginPath();
        ctx.arc(b.x, b.y, b.radius, 0, Math.PI * 2);
        ctx.strokeStyle = `hsla(${b.hue}, 95%, 80%, ${b.alpha * 0.7})`;
        ctx.lineWidth = 1;
        ctx.stroke();

        // Primary specular sheen
        ctx.beginPath();
        ctx.ellipse(
          b.x - b.radius * 0.32,
          b.y - b.radius * 0.32,
          b.radius * 0.22,
          b.radius * 0.11,
          -Math.PI / 4,
          0,
          Math.PI * 2
        );
        ctx.fillStyle = `rgba(255, 255, 255, ${Math.min(0.7, b.alpha + 0.3)})`;
        ctx.fill();

        // Secondary bottom rim reflection
        ctx.beginPath();
        ctx.arc(b.x, b.y, b.radius - 2.5, 0.45 * Math.PI, 0.8 * Math.PI);
        ctx.strokeStyle = `hsla(${b.hue}, 90%, 85%, ${b.alpha * 0.5})`;
        ctx.lineWidth = 1.4;
        ctx.stroke();

        ctx.restore();
      }

      // 2. Render sliced halves drifting apart & fading
      const halves = halvesRef.current;
      for (let i = halves.length - 1; i >= 0; i--) {
        const h = halves[i];
        h.x += h.vx;
        h.y += h.vy;
        h.rotation += h.rotSpeed;
        h.alpha -= 0.022; // Fades out over ~45 frames (~0.7s)

        if (h.alpha <= 0) {
          halves.splice(i, 1);
          continue;
        }

        ctx.save();
        ctx.translate(h.x, h.y);
        ctx.rotate(h.rotation);

        ctx.beginPath();
        if (h.side === "top") {
          ctx.arc(0, 0, h.radius, 0, Math.PI);
        } else {
          ctx.arc(0, 0, h.radius, Math.PI, Math.PI * 2);
        }
        ctx.closePath();

        const grad = ctx.createRadialGradient(
          -h.radius * 0.2,
          -h.radius * 0.2,
          h.radius * 0.08,
          0,
          0,
          h.radius
        );
        grad.addColorStop(0, `hsla(${h.hue}, 95%, 85%, ${h.alpha * 0.75})`);
        grad.addColorStop(0.5, `hsla(${h.hue}, 80%, 60%, ${h.alpha * 0.2})`);
        grad.addColorStop(1, `hsla(${h.hue}, 90%, 75%, ${h.alpha * 0.65})`);
        ctx.fillStyle = grad;
        ctx.fill();

        ctx.strokeStyle = `hsla(${h.hue}, 95%, 85%, ${h.alpha * 0.8})`;
        ctx.lineWidth = 1.2;
        ctx.stroke();

        ctx.restore();
      }

      // 3. Render slice sparks
      const sparks = sparksRef.current;
      for (let i = sparks.length - 1; i >= 0; i--) {
        const s = sparks[i];
        s.x += s.vx;
        s.y += s.vy;
        s.alpha -= 0.035;
        if (s.alpha <= 0) {
          sparks.splice(i, 1);
          continue;
        }
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.radius, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${s.hue}, 95%, 85%, ${s.alpha})`;
        ctx.fill();
      }

      // Replenish ambient bubbles if below 8
      while (bubbles.length < 8 && height > 0 && width > 0) {
        bubbles.push(createBubble(Math.random() * width, height + 40));
      }

      animFrameRef.current = requestAnimationFrame(render);
    };

    animFrameRef.current = requestAnimationFrame(render);

    // Pause when tab is hidden or offscreen, and reset pointer state
    const onVisibilityChange = () => {
      isVisibleRef.current = !document.hidden;
      if (document.hidden) resetPointerState();
    };
    document.addEventListener("visibilitychange", onVisibilityChange);

    const io = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        isVisibleRef.current = entry.isIntersecting && !document.hidden;
        if (!entry.isIntersecting) resetPointerState();
      }
    });
    io.observe(canvas);

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      canvas.removeEventListener("pointerdown", onPointerDown);
      canvas.removeEventListener("pointermove", onPointerMove);
      canvas.removeEventListener("pointerup", onPointerUp);
      canvas.removeEventListener("pointercancel", onPointerCancel);
      canvas.removeEventListener("pointerleave", onPointerLeave);
      window.removeEventListener("blur", onWindowBlur);
      ro.disconnect();
      io.disconnect();
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className={`h-full w-full ${className}`}
      style={{ touchAction: "none" }}
      aria-hidden="true"
    />
  );
}
