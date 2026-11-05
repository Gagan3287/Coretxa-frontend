"use client";

import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { anton } from "@/lib/fonts";

gsap.registerPlugin(ScrollTrigger);

const ONCE_PER_SESSION = true; // Skip intro for returning visitors in current session
const WAVE_PERIOD = 400; // width of one full wave
const WAVE_HEIGHT = 20; // how tall the wave crests are
const LEVEL_EMPTY = 335; // wave position when the word is empty
const LEVEL_FULL = 10; // wave position when the word is full

// Plays once per page load. Moving around the site afterwards uses the blue-lines transition instead.
let introPlayedThisLoad = false;

const useIsoLayoutEffect = typeof window !== "undefined" ? useLayoutEffect : useEffect;

function buildWave() {
  const half = WAVE_PERIOD / 2;
  const start = -WAVE_PERIOD * 2;
  const end = 2200;
  let d = `M ${start} 0 Q ${start + half / 2} ${-WAVE_HEIGHT} ${start + half} 0`;
  for (let x = start + half * 2; x <= end; x += half) d += ` T ${x} 0`;
  return `${d} V 700 H ${start} Z`;
}
const WAVE = buildWave();

const wait = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

const pageLoaded = () =>
  new Promise<void>((resolve) => {
    if (document.readyState === "complete") resolve();
    else window.addEventListener("load", () => resolve(), { once: true });
  });

export default function IntroLoader() {
  const uid = useId().replace(/[^a-zA-Z0-9]/g, "");
  const overlay = useRef<HTMLDivElement>(null);
  const content = useRef<HTMLDivElement>(null);
  const textRef = useRef<SVGTextElement>(null);
  const waveFront = useRef<SVGPathElement>(null);
  const waveBack = useRef<SVGPathElement>(null);
  const numRef = useRef<HTMLSpanElement>(null);
  const [gone, setGone] = useState(false);

  useIsoLayoutEffect(() => {
    const html = document.documentElement;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let seen = false;
    try {
      seen = ONCE_PER_SESSION && sessionStorage.getItem("cx-intro") === "1";
    } catch {}
    const transitioning = html.dataset.transition === "covering";
    if (reduced || seen || introPlayedThisLoad || transitioning) {
      // During a page transition, the transition itself releases the page animations.
      if (!transitioning) html.dataset.intro = "done";
      setGone(true);
      return;
    }
    html.dataset.intro = "playing";
  }, []);

  useEffect(() => {
    const html = document.documentElement;
    if (html.dataset.intro !== "playing") return;
    const overlayEl = overlay.current;
    const contentEl = content.current;
    const front = waveFront.current;
    const back = waveBack.current;
    if (!overlayEl || !contentEl || !front || !back) return;

    let cancelled = false;
    const tweens: gsap.core.Animation[] = [];
    const state = { p: 0 };

    const block = (e: Event) => {
      e.preventDefault();
      e.stopPropagation();
    };
    window.addEventListener("wheel", block, { capture: true, passive: false });
    window.addEventListener("touchmove", block, { capture: true, passive: false });

    const unblock = () => {
      window.removeEventListener("wheel", block, { capture: true });
      window.removeEventListener("touchmove", block, { capture: true });
      document.documentElement.style.overflow = "";
      document.body.style.overflow = "";
      ScrollTrigger.refresh();
    };

    const render = () => {
      const p = state.p;
      if (numRef.current) numRef.current.textContent = String(Math.round(p));
      const y = LEVEL_EMPTY - (p / 100) * (LEVEL_EMPTY - LEVEL_FULL);
      gsap.set(front, { y });
      gsap.set(back, { y: y - 12 });
    };
    render();

    tweens.push(gsap.to(front, { x: -WAVE_PERIOD, duration: 1.6, ease: "none", repeat: -1 }));
    tweens.push(gsap.fromTo(back, { x: -WAVE_PERIOD }, { x: 0, duration: 2.2, ease: "none", repeat: -1 }));

    const progressTo = (vars: gsap.TweenVars) =>
      new Promise<void>((resolve) => {
        tweens.push(gsap.to(state, { ...vars, onUpdate: render, onComplete: resolve }));
      });

    const finish = () => {
      introPlayedThisLoad = true;
      try {
        sessionStorage.setItem("cx-intro", "1");
      } catch {}
      unblock();
      setGone(true);
    };

    // Hard safety failsafe: unblock and reveal if anything pauses or takes >2.4s
    const safetyTimer = window.setTimeout(() => {
      unblock();
      html.dataset.intro = "done";
      window.dispatchEvent(new Event("cortexa:intro-done"));
      setGone(true);
    }, 2400);

    const run = async () => {
      const family = textRef.current ? getComputedStyle(textRef.current).fontFamily : "";
      await Promise.race([
        document.fonts.load(`300px ${family}`, "CORTEXA").catch(() => []),
        wait(400),
      ]);
      if (cancelled) return;

      tweens.push(gsap.to(contentEl, { opacity: 1, duration: 0.35, ease: "power2.out" }));
      await progressTo({ p: 85, duration: 0.85, ease: "power2.out" });
      if (cancelled) return;

      await Promise.race([pageLoaded(), wait(500)]);
      if (cancelled) return;

      await progressTo({ p: 100, duration: 0.35, ease: "power2.inOut" });
      if (cancelled) return;
      await wait(120);
      if (cancelled) return;

      window.scrollTo(0, 0);
      tweens.push(gsap.to(contentEl, { scale: 1.04, opacity: 0, duration: 0.4, ease: "power2.in" }));
      tweens.push(
        gsap.to(overlayEl, {
          yPercent: -100,
          duration: 0.7,
          delay: 0.1,
          ease: "power4.inOut",
          onComplete: finish,
        })
      );
      tweens.push(
        gsap.delayedCall(0.3, () => {
          unblock();
          html.dataset.intro = "done";
          window.dispatchEvent(new Event("cortexa:intro-done"));
        })
      );
    };
    run();

    return () => {
      cancelled = true;
      window.clearTimeout(safetyTimer);
      tweens.forEach((t) => t.kill());
      unblock();
      html.dataset.intro = "done";
      window.dispatchEvent(new Event("cortexa:intro-done"));
    };
  }, []);

  if (gone) return null;

  const textProps = {
    x: 500,
    y: 300,
    fontSize: 300,
    textAnchor: "middle" as const,
    textLength: 960,
    lengthAdjust: "spacingAndGlyphs" as const,
  };

  return (
    <div
      ref={overlay}
      className="fixed inset-0 z-[100] overflow-hidden bg-[#05070f]"
      style={{
        backgroundImage: "radial-gradient(60% 50% at 50% 50%, rgba(99,102,241,0.2), transparent)",
      }}
    >
      <span className="sr-only">Loading Cortexa</span>

      <div ref={content} className="absolute inset-0" style={{ opacity: 0 }} aria-hidden="true">
        <div className="absolute inset-0 grid place-items-center">
          <svg
            viewBox="0 0 1000 340"
            className="w-[min(92vw,1700px)] overflow-visible"
            style={{ filter: "drop-shadow(0 0 28px rgba(99,102,241,0.35))" }}
          >
            <defs>
              <linearGradient id={`${uid}g`} x1="0" y1="0" x2="1" y2="0">
                <stop offset="0" stopColor="#818cf8" />
                <stop offset="1" stopColor="#22d3ee" />
              </linearGradient>
              <clipPath id={`${uid}cf`}>
                <path ref={waveFront} d={WAVE} />
              </clipPath>
              <clipPath id={`${uid}cb`}>
                <path ref={waveBack} d={WAVE} />
              </clipPath>
            </defs>
            <text ref={textRef} {...textProps} className={anton.className} fill="#f1f0ea">
              CORTEXA
            </text>
            <text
              {...textProps}
              className={anton.className}
              fill="#22d3ee"
              fillOpacity={0.45}
              clipPath={`url(#${uid}cb)`}
            >
              CORTEXA
            </text>
            <text
              {...textProps}
              className={anton.className}
              fill={`url(#${uid}g)`}
              clipPath={`url(#${uid}cf)`}
            >
              CORTEXA
            </text>
          </svg>
        </div>

        <p className="absolute bottom-8 left-20 font-mono text-sm tracking-[0.3em] text-white/50 md:left-24">
          INITIALIZING CORTEXA...
        </p>

        <div
          className={`${anton.className} pointer-events-none absolute bottom-8 right-6 text-[clamp(4rem,12vw,11rem)] leading-none text-[#f1f0ea] md:bottom-10 md:right-12`}
        >
          <span ref={numRef}>0</span>
          <span>%</span>
        </div>
      </div>
    </div>
  );
}
