"use client";

import { useEffect, useRef } from "react";

type Rgb = [number, number, number];

interface Props {
  className?: string;
  /** particles per 10,000 px of area */
  density?: number;
  maxParticles?: number;
  /** max distance (px) at which two particles are linked */
  linkDistance?: number;
  /** cursor influence radius (px) */
  mouseRadius?: number;
  /** 0 turns the cursor effect off, 1 is the default pull */
  mouseStrength?: number;
  /** base drift speed (px per second) */
  speed?: number;
}

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  phase: number;
  spd: number;
  r: number;
  violet: boolean;
}

const LEVELS = 4;

function hexToRgb(hex: string): Rgb {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim());
  if (!m) return [129, 140, 248];
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

const rgba = (c: Rgb, a: number) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;

export default function ParticleNetwork({
  className = "",
  density = 0.55,
  maxParticles = 90,
  linkDistance = 140,
  mouseRadius = 190,
  mouseStrength = 1,
  speed = 14,
}: Props) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvasEl = ref.current;
    const context = canvasEl?.getContext("2d");
    if (!canvasEl || !context) return;
    const canvas: HTMLCanvasElement = canvasEl;
    const ctx: CanvasRenderingContext2D = context;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let w = 0;
    let h = 0;
    let linkDist = linkDistance;
    const ps: Particle[] = [];
    const mouse = { x: 0, y: 0, tx: 0, ty: 0, inside: false, influence: 0, seen: false };

    let cyanRgb: Rgb = [34, 211, 238];
    let violetRgb: Rgb = [129, 140, 248];
    let lineRgb: Rgb = cyanRgb;

    const readColors = () => {
      const s = getComputedStyle(document.documentElement);
      cyanRgb = hexToRgb(s.getPropertyValue("--secondary"));
      violetRgb = hexToRgb(s.getPropertyValue("--primary"));
      const mix = (i: number) => Math.round(cyanRgb[i] * 0.65 + violetRgb[i] * 0.35);
      lineRgb = [mix(0), mix(1), mix(2)];
    };
    readColors();
    const themeObserver = new MutationObserver(() => {
      readColors();
      if (reduced) draw();
    });
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

    const makeParticle = (): Particle => {
      const phase = Math.random() * Math.PI * 2;
      const spd = speed * (0.5 + Math.random() * 0.8);
      return {
        x: Math.random() * w,
        y: Math.random() * h,
        vx: Math.cos(phase) * spd,
        vy: Math.sin(phase) * spd,
        phase,
        spd,
        r: 1 + Math.random() * 1.4,
        violet: Math.random() < 0.28,
      };
    };

    const buckets: number[][] = Array.from({ length: LEVELS }, () => []);

    function draw() {
      ctx.clearRect(0, 0, w, h);
      const n = ps.length;
      const L2 = linkDist * linkDist;
      buckets.forEach((b) => (b.length = 0));

      for (let i = 0; i < n; i++) {
        const a = ps[i];
        for (let j = i + 1; j < n; j++) {
          const b = ps[j];
          const dx = a.x - b.x;
          if (dx > linkDist || dx < -linkDist) continue;
          const dy = a.y - b.y;
          const d2 = dx * dx + dy * dy;
          if (d2 >= L2) continue;
          const t = 1 - Math.sqrt(d2) / linkDist;
          const level = Math.min(LEVELS - 1, Math.floor(t * LEVELS));
          buckets[level].push(a.x, a.y, b.x, b.y);
        }
      }

      ctx.lineWidth = 1;
      for (let l = 0; l < LEVELS; l++) {
        const seg = buckets[l];
        if (!seg.length) continue;
        ctx.strokeStyle = rgba(lineRgb, 0.08 + (l / (LEVELS - 1)) * 0.27);
        ctx.beginPath();
        for (let k = 0; k < seg.length; k += 4) {
          ctx.moveTo(seg[k], seg[k + 1]);
          ctx.lineTo(seg[k + 2], seg[k + 3]);
        }
        ctx.stroke();
      }

      const infl = Math.min(1, mouse.influence) * mouseStrength;
      if (infl > 0.02) {
        const R = mouseRadius * 1.15;
        ctx.lineWidth = 1.2;
        for (const p of ps) {
          const d = Math.hypot(p.x - mouse.x, p.y - mouse.y);
          if (d >= R) continue;
          ctx.strokeStyle = rgba(cyanRgb, (1 - d / R) * 0.6 * Math.min(1, infl));
          ctx.beginPath();
          ctx.moveTo(mouse.x, mouse.y);
          ctx.lineTo(p.x, p.y);
          ctx.stroke();
        }
      }

      for (const isViolet of [false, true]) {
        ctx.fillStyle = rgba(isViolet ? violetRgb : cyanRgb, isViolet ? 0.75 : 0.85);
        ctx.beginPath();
        for (const p of ps) {
          if (p.violet !== isViolet) continue;
          ctx.moveTo(p.x + p.r, p.y);
          ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        }
        ctx.fill();
      }
    }

    const update = (dt: number) => {
      mouse.x += (mouse.tx - mouse.x) * (1 - Math.exp(-dt * 10));
      mouse.y += (mouse.ty - mouse.y) * (1 - Math.exp(-dt * 10));
      mouse.influence += ((mouse.inside ? 1 : 0) - mouse.influence) * (1 - Math.exp(-dt * 2.5));
      const infl = Math.min(1, mouse.influence) * mouseStrength;
      const MAX_SPEED = 260;

      for (const p of ps) {
        p.phase += (Math.random() - 0.5) * 6 * dt;
        const ease = Math.min(1, dt * 1.5);
        p.vx += (Math.cos(p.phase) * p.spd - p.vx) * ease;
        p.vy += (Math.sin(p.phase) * p.spd - p.vy) * ease;

        if (infl > 0.01) {
          const dx = mouse.x - p.x;
          const dy = mouse.y - p.y;
          const d = Math.hypot(dx, dy);
          if (d < mouseRadius && d > 0.001) {
            const f = 1 - d / mouseRadius;
            const near = Math.min(1, Math.max(0, (d - 28) / 50));
            const a = 520 * f * near * infl;
            p.vx += (dx / d) * a * dt;
            p.vy += (dy / d) * a * dt;
          }
        }

        const sp = Math.hypot(p.vx, p.vy);
        if (sp > MAX_SPEED) {
          p.vx *= MAX_SPEED / sp;
          p.vy *= MAX_SPEED / sp;
        }

        p.x += p.vx * dt;
        p.y += p.vy * dt;
        if (p.x < -30) p.x = w + 30;
        else if (p.x > w + 30) p.x = -30;
        if (p.y < -30) p.y = h + 30;
        else if (p.y > h + 30) p.y = -30;
      }
    };

    const resize = () => {
      const r = canvas.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return;
      if (w > 0 && h > 0) {
        for (const p of ps) {
          p.x *= r.width / w;
          p.y *= r.height / h;
        }
      }
      w = r.width;
      h = r.height;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      linkDist = w < 768 ? linkDistance * 0.75 : linkDistance;
      const cap = w < 768 ? Math.min(maxParticles, 50) : maxParticles;
      const target = Math.max(24, Math.min(cap, Math.round(((w * h) / 10000) * density)));
      while (ps.length < target) ps.push(makeParticle());
      while (ps.length > target) ps.pop();
      if (reduced) draw();
    };

    let raf = 0;
    let running = false;
    let visible = false;
    let last = 0;

    const frame = (now: number) => {
      if (!running) return;
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      update(dt);
      draw();
      raf = requestAnimationFrame(frame);
    };
    const start = () => {
      if (reduced || running || !visible || document.hidden) return;
      running = true;
      last = performance.now();
      raf = requestAnimationFrame(frame);
    };
    const stop = () => {
      running = false;
      cancelAnimationFrame(raf);
    };

    const onPointerMove = (e: PointerEvent) => {
      if (e.pointerType === "touch") return;
      const r = canvas.getBoundingClientRect();
      const x = e.clientX - r.left;
      const y = e.clientY - r.top;
      mouse.inside = x >= 0 && y >= 0 && x <= r.width && y <= r.height;
      mouse.tx = x;
      mouse.ty = y;
      if (!mouse.seen) {
        mouse.x = x;
        mouse.y = y;
        mouse.seen = true;
      }
    };
    const onLeave = () => {
      mouse.inside = false;
    };
    const onVisibility = () => (document.hidden ? stop() : start());

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(canvas);

    const intersection = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (visible) start();
      else stop();
    });
    intersection.observe(canvas);

    if (!reduced) {
      window.addEventListener("pointermove", onPointerMove, { passive: true });
      document.documentElement.addEventListener("mouseleave", onLeave);
      window.addEventListener("blur", onLeave);
      document.addEventListener("visibilitychange", onVisibility);
    }

    return () => {
      stop();
      resizeObserver.disconnect();
      intersection.disconnect();
      themeObserver.disconnect();
      window.removeEventListener("pointermove", onPointerMove);
      document.documentElement.removeEventListener("mouseleave", onLeave);
      window.removeEventListener("blur", onLeave);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [density, maxParticles, linkDistance, mouseRadius, mouseStrength, speed]);

  return (
    <canvas
      ref={ref}
      aria-hidden="true"
      className={`pointer-events-none ${className}`}
    />
  );
}