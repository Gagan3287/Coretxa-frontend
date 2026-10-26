"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { anton } from "@/lib/fonts";

const SPEED = 0.8; // pixels the bands move per pixel scrolled
const COPIES = 4;

const defaultA = ["Your docs", "Sources shown", "Any website", "Light & dark", "One snippet"];
const defaultB = ["Build", "Customize", "Deploy", "Chat", "Grounded answers"];

const mod = (n: number, m: number) => ((n % m) + m) % m;

function Group({ items, starClass }: { items: string[]; starClass: string }) {
  return (
    <div className="flex shrink-0 items-center">
      {items.map((t) => (
        <span key={t} className="flex items-center whitespace-nowrap">
          <span className="px-[0.5em]">{t}</span>
          <span className={`px-[0.25em] ${starClass}`}>✦</span>
        </span>
      ))}
    </div>
  );
}

interface Props {
  itemsA?: string[];
  itemsB?: string[];
  srText?: string;
  /** swaps the tilt and the scroll direction of both bands */
  flip?: boolean;
  /** extra classes for the wrapper, e.g. a negative top margin */
  className?: string;
}

export default function Marquee({
  itemsA = defaultA,
  itemsB = defaultB,
  srText = "Cortexa answers from your docs, shows its sources, works on any website and installs with one snippet.",
  flip = false,
  className = "",
}: Props) {
  const root = useRef<HTMLDivElement>(null);
  const trackA = useRef<HTMLDivElement>(null);
  const trackB = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = root.current;
    const a = trackA.current;
    const b = trackB.current;
    if (!el || !a || !b) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let wA = 0;
    let wB = 0;
    const measure = () => {
      wA = (a.firstElementChild as HTMLElement | null)?.offsetWidth ?? 0;
      wB = (b.firstElementChild as HTMLElement | null)?.offsetWidth ?? 0;
    };
    measure();
    const resizeObserver = new ResizeObserver(measure);
    resizeObserver.observe(a);
    resizeObserver.observe(b);
    document.fonts?.ready.then(measure);

    let cur = window.scrollY * SPEED;
    const toLeft = (w: number, off: number) => `translate3d(${-mod(cur + off, w)}px,0,0)`;
    const toRight = (w: number, off: number) => `translate3d(${-w + mod(cur + off, w)}px,0,0)`;

    const tick = () => {
      const target = window.scrollY * SPEED;
      cur += (target - cur) * 0.12;
      if (wA) a.style.transform = flip ? toRight(wA, 0) : toLeft(wA, 0);
      if (wB) b.style.transform = flip ? toLeft(wB, wB * 0.37) : toRight(wB, wB * 0.37);
    };

    const io = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        cur = window.scrollY * SPEED;
        tick();
        gsap.ticker.add(tick);
      } else {
        gsap.ticker.remove(tick);
      }
    });
    io.observe(el);

    return () => {
      gsap.ticker.remove(tick);
      io.disconnect();
      resizeObserver.disconnect();
    };
  }, [flip]);

  const tiltA = flip ? 3 : -3;
  const tiltB = flip ? -3 : 3;

  return (
    <>
      <p className="sr-only">{srText}</p>
       <div ref={root} aria-hidden="true" className={`relative h-[200px] overflow-hidden sm:h-[260px] md:h-[320px] ${className}`}>
        <div
          className={`${anton.className} absolute left-[-10vw] top-1/2 w-[120vw] py-2 text-[clamp(1.6rem,4.6vw,4.5rem)] uppercase leading-none text-[#05070f]`}
          style={{
            transform: `translateY(-50%) rotate(${tiltB}deg)`,
            background: "linear-gradient(90deg, var(--primary), var(--secondary))",
          }}
        >
          <div ref={trackB} className="flex w-max will-change-transform">
            {Array.from({ length: COPIES }, (_, i) => (
              <Group key={i} items={itemsB} starClass="text-[#05070f]" />
            ))}
          </div>
        </div>

        <div
          className={`${anton.className} absolute left-[-10vw] top-1/2 z-10 w-[120vw] border-y-2 border-secondary bg-[#05070f] py-2 text-[clamp(1.6rem,4.6vw,4.5rem)] uppercase leading-none text-secondary`}
          style={{ transform: `translateY(-50%) rotate(${tiltA}deg)` }}
        >
          <div ref={trackA} className="flex w-max will-change-transform">
            {Array.from({ length: COPIES }, (_, i) => (
              <Group key={i} items={itemsA} starClass="text-primary" />
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
