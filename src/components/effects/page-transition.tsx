"use client";

import { useEffect, useRef } from "react";
import { usePathname, useRouter } from "next/navigation";
import gsap from "gsap";
import { NAVIGATE_EVENT } from "@/lib/utils/navigate";

const BARS = 12;
const STAGGER = 0.04;

// Moving between different areas plays the transition. Moving inside one area does not.
function areaOf(path: string) {
  if (path === "/") return "home";
  if (path.startsWith("/dashboard")) return "dashboard";
  return path;
}

export default function PageTransition() {
  const router = useRouter();
  const pathname = usePathname();
  const root = useRef<HTMLDivElement>(null);
  const busy = useRef(false);
  const pending = useRef(false);
  const failsafe = useRef<number | null>(null);
  const routerRef = useRef(router);
  const goRef = useRef<(href: string) => void>(() => {});

  useEffect(() => {
    routerRef.current = router;
  }, [router]);

  const reveal = () => {
    if (!pending.current) return;
    pending.current = false;
    if (failsafe.current) window.clearTimeout(failsafe.current);
    const el = root.current;
    if (!el) return;
    const bars = el.querySelectorAll<HTMLElement>("[data-bar]");
    const html = document.documentElement;

    gsap.set(bars, { transformOrigin: "50% 0%" });
    gsap.to(bars, {
      scaleY: 0,
      duration: 0.6,
      ease: "power3.inOut",
      stagger: { each: STAGGER },
      onComplete: () => {
        busy.current = false;
        el.style.pointerEvents = "none";
      },
    });
    gsap.delayedCall(0.2, () => {
      delete html.dataset.transition;
      html.dataset.intro = "done";
      window.dispatchEvent(new Event("cortexa:intro-done"));
    });
  };

  const go = (href: string) => {
    const el = root.current;
    const target = new URL(href, window.location.href);
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const same =
      target.pathname === window.location.pathname ||
      areaOf(target.pathname) === areaOf(window.location.pathname);

    if (!el || reduced || same) {
      routerRef.current.push(href);
      return;
    }
    if (busy.current) return;
    busy.current = true;

    const html = document.documentElement;
    html.dataset.transition = "covering";
    html.dataset.intro = "playing";
    el.style.pointerEvents = "auto";

    const bars = el.querySelectorAll<HTMLElement>("[data-bar]");
    gsap.set(bars, { transformOrigin: "50% 100%" });
    gsap.to(bars, {
      scaleY: 1,
      duration: 0.55,
      ease: "power3.inOut",
      stagger: { each: STAGGER },
      onComplete: () => {
        pending.current = true;
        routerRef.current.push(href);
        failsafe.current = window.setTimeout(reveal, 3500);
      },
    });
  };

  useEffect(() => {
    goRef.current = go;
  });

  // Plays the reveal once the new route has rendered.
  useEffect(() => {
    if (!pending.current) return;
    let second = 0;
    const first = requestAnimationFrame(() => {
      second = requestAnimationFrame(reveal);
    });
    return () => {
      cancelAnimationFrame(first);
      cancelAnimationFrame(second);
    };
  }, [pathname]);

  // Catches clicks on internal links and calls to navigateWithTransition().
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = (e.target as Element | null)?.closest?.("a");
      if (!a) return;
      const href = a.getAttribute("href");
      if (!href || !href.startsWith("/") || href.startsWith("//")) return;
      if (a.target && a.target !== "_self") return;
      if (a.hasAttribute("download")) return;

      const url = new URL(href, window.location.href);
      if (url.origin !== window.location.origin) return;
      if (url.pathname === window.location.pathname) return;
      if (areaOf(url.pathname) === areaOf(window.location.pathname)) return;
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

      e.preventDefault();
      e.stopPropagation();
      goRef.current(url.pathname + url.search + url.hash);
    };

    const onNavigate = (e: Event) => {
      const href = (e as CustomEvent<string>).detail;
      if (typeof href === "string") goRef.current(href);
    };

    document.addEventListener("click", onClick, true);
    window.addEventListener(NAVIGATE_EVENT, onNavigate);
    return () => {
      document.removeEventListener("click", onClick, true);
      window.removeEventListener(NAVIGATE_EVENT, onNavigate);
      if (failsafe.current) window.clearTimeout(failsafe.current);
    };
  }, []);

  return (
    <div ref={root} aria-hidden="true" className="pointer-events-none fixed inset-0 z-[110] flex overflow-hidden">
      {Array.from({ length: BARS }, (_, i) => (
        <div
          key={i}
          data-bar
          className="h-full flex-1"
          style={{
            transform: "scaleY(0)",
            transformOrigin: "50% 100%",
            marginRight: -1,
            background: "linear-gradient(180deg, #22d3ee 0%, #4f46e5 55%, #1e1b4b 100%)",
            boxShadow: "0 0 30px rgba(34,211,238,0.5)",
          }}
        />
      ))}
    </div>
  );
}