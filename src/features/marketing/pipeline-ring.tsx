"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { Cpu, MessageSquare, Palette, Quote, Rocket, UploadCloud } from "lucide-react";
import ParticleNetwork from "@/components/effects/particle-network";
import { anton } from "@/lib/fonts";

const AUTO_SPEED = 8; // degrees per second while idle
const RESUME_AFTER_MS = 4_000; // idle time before auto-rotation and the default view return
const DRAG_YAW = 0.35; // degrees of spin per horizontal pixel
const DRAG_TILT = 0.25; // degrees of tilt per vertical pixel
const TILT_DEFAULT = -12; // negative looks down onto the ring
const TILT_MIN = -88; // almost straight down
const TILT_MAX = 40; // slightly from below
const RIBS = 36; // vertical mesh lines
const DIAGONALS = 24; // diagonal pairs in the mesh
const DIAGONAL_TILT = 16;
const ZIGZAG = 0.16; // how far cards sit above / below the middle, as a fraction of the radius
const RING_LEVELS = [-0.5, -0.25, 0, 0.25, 0.5];

const cards = [
  { icon: UploadCloud, title: "Upload", text: "Add your PDFs to a bot." },
  { icon: Cpu, title: "Process", text: "Documents are prepared so they can be searched." },
  { icon: MessageSquare, title: "Ask", text: "Visitors ask in plain language." },
  { icon: Quote, title: "Cite", text: "Answers can show the document they came from." },
  { icon: Palette, title: "Brand", text: "Set the name, color, greeting and position." },
  { icon: Rocket, title: "Deploy", text: "Use a script, an iframe or a hosted page." },
];

const STEP = 360 / cards.length;
const clamp = (v: number, min: number, max: number) => Math.min(max, Math.max(min, v));

function Card({ icon: Icon, title, text, n }: (typeof cards)[number] & { n: number }) {
  return (
    <div
      className="flex h-full flex-col justify-between overflow-hidden rounded-[0.7em] border border-border bg-surface p-[1.2em] shadow-2xl"
      style={{ borderLeftColor: "var(--secondary)", borderLeftWidth: "0.25em" }}
    >
      <div className="flex items-center justify-between">
        <span className="grid h-[2.2em] w-[2.2em] place-items-center rounded-[0.6em] bg-primary/15 text-primary">
          <Icon size="1.2em" />
        </span>
        <span className="font-mono text-[0.7em] tracking-widest text-secondary">
          {String(n + 1).padStart(2, "0")} / {String(cards.length).padStart(2, "0")}
        </span>
      </div>
      <div>
        <h3 className={`${anton.className} text-[2.4em] uppercase leading-none tracking-wide`}>{title}</h3>
        <p className="mt-[0.4em] hidden text-[0.85em] leading-snug text-muted sm:block">{text}</p>
      </div>
    </div>
  );
}

export default function PipelineRing() {
  const stage = useRef<HTMLDivElement>(null);
  const tiltRef = useRef<HTMLDivElement>(null);
  const ring = useRef<HTMLDivElement>(null);
  const cardRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    const stageEl = stage.current;
    const tiltEl = tiltRef.current;
    const ringEl = ring.current;
    if (!stageEl || !tiltEl || !ringEl) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let yaw = 0;
    let tilt = TILT_DEFAULT;
    let yawVel = 0;
    let tiltVel = 0;
    let autoFactor = 1;
    let dragging = false;
    let lastX = 0;
    let lastY = 0;
    let lastT = 0;
    let lastInteraction = -Infinity;

    const onDown = (e: PointerEvent) => {
      if (e.pointerType === "mouse" && e.button !== 0) return;
      dragging = true;
      lastX = e.clientX;
      lastY = e.clientY;
      lastT = performance.now();
      lastInteraction = lastT;
      yawVel = 0;
      tiltVel = 0;
      autoFactor = 0;
      stageEl.setPointerCapture(e.pointerId);
    };

    const onMove = (e: PointerEvent) => {
      if (!dragging) return;
      const now = performance.now();
      const dt = Math.max(1, now - lastT) / 1000;
      const dYaw = (e.clientX - lastX) * DRAG_YAW;
      yaw += dYaw;
      yawVel = yawVel * 0.6 + (dYaw / dt) * 0.4;

      if (e.pointerType !== "touch") {
        const dTilt = -(e.clientY - lastY) * DRAG_TILT;
        tilt = clamp(tilt + dTilt, TILT_MIN, TILT_MAX);
        tiltVel = tiltVel * 0.6 + (dTilt / dt) * 0.4;
      }

      lastX = e.clientX;
      lastY = e.clientY;
      lastT = now;
      lastInteraction = now;
    };

    const onUp = (e: PointerEvent) => {
      if (!dragging) return;
      dragging = false;
      const now = performance.now();
      lastInteraction = now;
      if (now - lastT > 80) {
        yawVel = 0;
        tiltVel = 0;
      }
      if (stageEl.hasPointerCapture(e.pointerId)) stageEl.releasePointerCapture(e.pointerId);
    };

    stageEl.addEventListener("pointerdown", onDown);
    stageEl.addEventListener("pointermove", onMove);
    stageEl.addEventListener("pointerup", onUp);
    stageEl.addEventListener("pointercancel", onUp);

    const tick = (_time: number, deltaMs: number) => {
      const dt = Math.min(deltaMs, 50) / 1000;

      if (!dragging) {
        const idleLong = performance.now() - lastInteraction > RESUME_AFTER_MS;
        autoFactor += ((idleLong ? 1 : 0) - autoFactor) * (1 - Math.exp(-dt * 0.8));

        const decay = Math.exp(-dt * 2.2);
        yawVel *= decay;
        tiltVel *= decay;

        yaw += (yawVel + AUTO_SPEED * autoFactor) * dt;
        tilt += tiltVel * dt;
        if (idleLong) tilt += (TILT_DEFAULT - tilt) * (1 - Math.exp(-dt * 0.6));

        if (tilt <= TILT_MIN || tilt >= TILT_MAX) tiltVel = 0;
        tilt = clamp(tilt, TILT_MIN, TILT_MAX);
      }

      tiltEl.style.transform = `rotateX(${tilt}deg)`;
      ringEl.style.transform = `rotateY(${yaw}deg)`;

      for (let i = 0; i < cardRefs.current.length; i++) {
        const el = cardRefs.current[i];
        if (!el) continue;
        const facing = Math.cos(((i * STEP + yaw) * Math.PI) / 180);
        el.style.opacity = String(0.4 + 0.6 * Math.max(0, facing));
      }
    };

    const io = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) gsap.ticker.add(tick);
      else gsap.ticker.remove(tick);
    });
    io.observe(stageEl);

    return () => {
      gsap.ticker.remove(tick);
      io.disconnect();
      stageEl.removeEventListener("pointerdown", onDown);
      stageEl.removeEventListener("pointermove", onMove);
      stageEl.removeEventListener("pointerup", onUp);
      stageEl.removeEventListener("pointercancel", onUp);
    };
  }, []);

  return (
    <section
      aria-labelledby="ring-title"
      className="relative overflow-x-clip pt-16 [--h:calc(var(--r)*0.82)] [--r:clamp(200px,36vw,700px)] md:pt-24"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 animate-pulse [animation-duration:5s]"
        style={{
          background:
            "radial-gradient(45% 40% at 50% 64%, color-mix(in srgb, var(--secondary) 24%, transparent), transparent), radial-gradient(55% 45% at 50% 38%, color-mix(in srgb, var(--primary) 24%, transparent), transparent)",
        }}
      />

      <ParticleNetwork
        className="absolute inset-0 h-full w-full"
        density={0.3}
        maxParticles={60}
        linkDistance={0}
        mouseStrength={0}
        speed={10}
      />

      <div className="relative mx-auto max-w-[1440px] px-6 text-center md:px-8">
        <p className="font-mono text-sm tracking-widest text-secondary">INSIDE CORTEXA</p>
        <h2
          id="ring-title"
          className={`${anton.className} mt-3 text-[clamp(2.25rem,6vw,5.5rem)] uppercase leading-none tracking-wide`}
        >
          From documents to <span className="gradient-text">a live assistant.</span>
        </h2>
        <p className="mt-4 font-mono text-xs tracking-widest text-muted motion-reduce:hidden">
          DRAG TO ROTATE ↔ AND TILT ↕
        </p>
      </div>

      <div
        ref={stage}
        role="group"
        aria-label="3D carousel of Cortexa features. Drag to rotate and tilt."
        className="relative mx-auto mt-6 h-[calc(var(--r)*1.5)] w-full touch-pan-y select-none motion-reduce:hidden"
        style={{ perspective: "calc(var(--r) * 3)", perspectiveOrigin: "50% 42%" }}
      >
        <div
          ref={tiltRef}
          className="absolute left-1/2 top-[48%] h-0 w-0 [transform-style:preserve-3d] will-change-transform"
          style={{ transform: `rotateX(${TILT_DEFAULT}deg)` }}
        >
          <div ref={ring} className="absolute left-0 top-0 h-0 w-0 [transform-style:preserve-3d] will-change-transform">
            {[-0.5, 0.5].map((f) => (
              <div
                key={`disc-${f}`}
                className="absolute left-0 top-0 rounded-full"
                style={{
                  width: "calc(var(--r) * 2)",
                  height: "calc(var(--r) * 2)",
                  marginLeft: "calc(var(--r) * -1)",
                  marginTop: "calc(var(--r) * -1)",
                  background: `radial-gradient(circle, color-mix(in srgb, ${f > 0 ? "var(--secondary)" : "var(--primary)"} ${f > 0 ? 38 : 22}%, transparent), transparent 70%)`,
                  transform: `translateY(calc(var(--h) * ${f})) rotateX(90deg)`,
                }}
              />
            ))}

            {Array.from({ length: RIBS }, (_, i) => (
              <div
                key={`rib-${i}`}
                className="absolute left-0 top-0"
                style={{
                  width: 1,
                  height: "var(--h)",
                  marginTop: "calc(var(--h) / -2)",
                  background: "color-mix(in srgb, var(--secondary) 70%, transparent)",
                  boxShadow: "0 0 6px color-mix(in srgb, var(--secondary) 80%, transparent)",
                  transform: `rotateY(${(i * 360) / RIBS}deg) translateZ(var(--r))`,
                }}
              />
            ))}

            {Array.from({ length: DIAGONALS * 2 }, (_, i) => {
              const dir = i % 2 === 0 ? 1 : -1;
              const slot = Math.floor(i / 2);
              return (
                <div
                  key={`diag-${i}`}
                  className="absolute left-0 top-0"
                  style={{
                    width: 1,
                    height: "calc(var(--h) * 1.04)",
                    marginTop: "calc(var(--h) * -0.52)",
                    background: "color-mix(in srgb, var(--primary) 60%, transparent)",
                    boxShadow: "0 0 6px color-mix(in srgb, var(--primary) 80%, transparent)",
                    transform: `rotateY(${(slot * 360) / DIAGONALS + 180 / DIAGONALS}deg) translateZ(var(--r)) rotateZ(${dir * DIAGONAL_TILT}deg)`,
                  }}
                />
              );
            })}

            {RING_LEVELS.map((f) => {
              const edge = Math.abs(f) === 0.5;
              const color = f < 0 ? "var(--primary)" : "var(--secondary)";
              return (
                <div
                  key={`level-${f}`}
                  className="absolute left-0 top-0 rounded-full"
                  style={{
                    width: "calc(var(--r) * 2)",
                    height: "calc(var(--r) * 2)",
                    marginLeft: "calc(var(--r) * -1)",
                    marginTop: "calc(var(--r) * -1)",
                    border: edge
                      ? `5px solid ${color}`
                      : "1px solid color-mix(in srgb, var(--secondary) 45%, transparent)",
                    boxShadow: edge
                      ? `0 0 30px ${color}, 0 0 80px ${color}, inset 0 0 60px ${color}`
                      : undefined,
                    transform: `translateY(calc(var(--h) * ${f})) rotateX(90deg)`,
                  }}
                />
              );
            })}

            {cards.map((c, i) => (
              <div
                key={c.title}
                ref={(el) => {
                  cardRefs.current[i] = el;
                }}
                className="absolute left-0 top-0"
                style={{
                  width: "20em",
                  height: "12em",
                  marginLeft: "-10em",
                  marginTop: "-6em",
                  fontSize: "max(10px, calc(var(--r) * 0.028))",
                  transform: `rotateY(${i * STEP}deg) translateY(calc(var(--r) * ${i % 2 === 0 ? -ZIGZAG : ZIGZAG})) translateZ(calc(var(--r) * 1.03))`,
                }}
              >
                <Card {...c} n={i} />
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="relative mx-auto mt-12 hidden w-full max-w-5xl gap-4 px-6 motion-reduce:grid sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((c, i) => (
          <div key={c.title} className="h-48" style={{ fontSize: 16 }}>
            <Card {...c} n={i} />
          </div>
        ))}
      </div>
    </section>
  );
}