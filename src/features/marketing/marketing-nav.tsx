"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";
import ThemeToggle from "@/components/layout/theme-toggle";
import { getSession } from "@/lib/auth/session";

gsap.registerPlugin(useGSAP, ScrollTrigger);

const links = [
  { href: "#how", label: "How it works" },
  { href: "#use-cases", label: "Use cases" },
  { href: "#features", label: "Features" },
  { href: "/pricing", label: "Pricing" },
  { href: "#faq", label: "FAQ" },
];

export default function MarketingNav() {
  const nav = useRef<HTMLElement>(null);
  const [open, setOpen] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const session = getSession();
    if (session?.token) {
      const frame = requestAnimationFrame(() => {
        setIsLoggedIn(true);
      });
      return () => cancelAnimationFrame(frame);
    }
  }, []);

  useGSAP(
    () => {
      gsap.to(".nav-progress", {
        scaleX: 1,
        ease: "none",
        scrollTrigger: { start: 0, end: "max", scrub: 0.2 },
      });

      let hidden = false;
      ScrollTrigger.create({
        start: 0,
        end: "max",
        onUpdate: (self) => {
          const shouldHide = self.direction === 1 && self.scroll() > 240;
          if (shouldHide !== hidden) {
            hidden = shouldHide;
            gsap.to(nav.current, { yPercent: hidden ? -100 : 0, duration: 0.4, ease: "power3.out" });
          }
        },
      });
    },
    { scope: nav }
  );

  const resolveLink = (href: string) => {
    if (href.startsWith("#")) {
      return pathname === "/" ? href : `/${href}`;
    }
    return href;
  };

  return (
    <header ref={nav} className="fixed inset-x-0 top-0 z-40">
      <div className="border-b border-border bg-background/70 backdrop-blur-xl">
        <div className="mx-auto flex h-16 w-full max-w-[1440px] items-center justify-between px-6 md:px-8">
          <Link href="/" className="font-display text-xl font-bold tracking-tight">
            Cortex<span className="gradient-text">a</span>
          </Link>

          <nav className="hidden items-center gap-8 md:flex" aria-label="Main">
            {links.map((l) => (
              <a
                key={l.href}
                href={resolveLink(l.href)}
                className="text-sm text-muted transition hover:text-foreground"
              >
                {l.label}
              </a>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link
              href="/dashboard"
              className="hidden rounded-full bg-gradient-to-r from-primary to-secondary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-md transition-transform hover:-translate-y-0.5 sm:inline-flex"
            >
              Open Dashboard
            </Link>
            <button
              className="text-muted md:hidden"
              aria-label={open ? "Close menu" : "Open menu"}
              aria-expanded={open}
              onClick={() => setOpen((o) => !o)}
            >
              {open ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        </div>

        {open && (
          <nav className="border-t border-border px-6 py-4 md:hidden" aria-label="Mobile">
            {links.map((l) => (
              <a
                key={l.href}
                href={resolveLink(l.href)}
                onClick={() => setOpen(false)}
                className="block py-3 text-sm text-muted hover:text-foreground"
              >
                {l.label}
              </a>
            ))}
            <Link
              href="/dashboard"
              onClick={() => setOpen(false)}
              className="mt-2 block py-3 text-sm font-semibold text-secondary"
            >
              Open Dashboard
            </Link>
          </nav>
        )}
      </div>
      <div
        className="nav-progress h-0.5 origin-left scale-x-0"
        style={{ background: "linear-gradient(90deg, var(--primary), var(--secondary))" }}
      />
    </header>
  );
}