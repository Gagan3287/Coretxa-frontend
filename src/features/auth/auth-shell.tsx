"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import ParticleNetwork from "@/components/effects/particle-network";
import ScrambleText from "@/components/effects/scramble-text";
import { anton } from "@/lib/fonts";
import { whenIntroDone } from "@/lib/utils/intro-gate";
import TiltDevice from "./tilt-device";
import BubbleCanvas from "./bubble-canvas";
import LoginForm from "./login-form";
import RegisterForm from "./register-form";

gsap.registerPlugin(useGSAP);

interface Props {
  initialMode?: "login" | "register";
  tagline?: string[];
  description?: string;
  children?: React.ReactNode;
}

const LOGIN_TAGLINE = ["Welcome.", "Back to", "Cortexa."];
const LOGIN_DESC = "Pick up where you left off: your documents, your bots and your widget.";

const REGISTER_TAGLINE = ["Build.", "Brand.", "Deploy."];
const REGISTER_DESC = "Create your organization, upload your documents and put an assistant on your website.";

export default function AuthShell({
  initialMode = "login",
  tagline,
  description,
  children,
}: Props) {
  const root = useRef<HTMLDivElement>(null);
  const [mode, setMode] = useState<"login" | "register">(initialMode);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(prefers-reduced-motion: no-preference)", () => {
        const tl = gsap.timeline({ paused: true, defaults: { ease: "power3.out" } });
        tl.from(".auth-visual", { opacity: 0, x: -40, duration: 1 }, 0)
          .from(".auth-tagline", { opacity: 0, y: 40, duration: 0.9 }, 0.15)
          .from(".auth-reveal", { opacity: 0, y: 28, duration: 0.7, stagger: 0.08 }, 0.1);
        return whenIntroDone(() => tl.play());
      });
      return () => mm.revert();
    },
    { scope: root }
  );

  // Sync state with browser back/forward buttons
  useEffect(() => {
    const onPopState = () => {
      const path = window.location.pathname;
      if (path.startsWith("/register")) {
        setMode("register");
        document.title = "Create account | Cortexa";
      } else if (path.startsWith("/login")) {
        setMode("login");
        document.title = "Sign in | Cortexa";
      }
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const handleToggleMode = () => {
    const nextMode = mode === "login" ? "register" : "login";
    const nextUrl = nextMode === "login" ? "/login" : "/register";
    window.history.pushState(null, "", nextUrl);
    setMode(nextMode);
    document.title = nextMode === "login" ? "Sign in | Cortexa" : "Create account | Cortexa";
  };

  const currentTagline =
    mode === "login"
      ? (tagline ?? LOGIN_TAGLINE)
      : (tagline && initialMode === "register" ? tagline : REGISTER_TAGLINE);

  const currentDescription =
    mode === "login"
      ? (description ?? LOGIN_DESC)
      : (description && initialMode === "register" ? description : REGISTER_DESC);

  return (
    <div ref={root} className="relative min-h-screen overflow-hidden bg-background text-foreground">
      <ParticleNetwork
        className="absolute inset-0 h-full w-full"
        density={0.45}
        linkDistance={130}
        mouseRadius={170}
        mouseStrength={1}
        speed={12}
      />

      <Link
        href="/"
        className="absolute left-6 top-8 z-20 font-mono text-xs tracking-[0.18em] text-muted transition hover:text-secondary md:left-12"
      >
        <ScrambleText text="← RETURN TO BASE" />
      </Link>

      <div className="relative z-10 grid min-h-screen lg:grid-cols-2">
        {/* Left Section: Bubble canvas background + centered TiltDevice + Tagline (no divider line) */}
        <section className="relative hidden flex-col px-12 pb-12 pt-28 lg:flex">
          <div className="pointer-events-auto absolute inset-0 overflow-hidden">
            <BubbleCanvas />
          </div>

          <div className="pointer-events-none relative z-10 grid flex-1 place-items-center">
            <div className="pointer-events-auto">
              <TiltDevice />
            </div>
          </div>

          <div className="auth-tagline relative z-10 transition-opacity duration-300">
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">{"// CORTEXA"}</p>
            <h2
              className={`${anton.className} mt-4 text-[clamp(3rem,5.2vw,5.5rem)] uppercase leading-[0.92] tracking-[0.01em]`}
            >
              {currentTagline.map((line, i) => (
                <span key={line} className="block">
                  <span
                    className={`inline-block cursor-default transition-all duration-300 hover:text-secondary hover:[text-shadow:0_0_32px_var(--secondary)] ${
                      i === currentTagline.length - 1 ? "gradient-text" : ""
                    }`}
                  >
                    {line}
                  </span>
                </span>
              ))}
            </h2>
            <p className="mt-5 max-w-md text-sm text-muted">{currentDescription}</p>
          </div>
        </section>

        {/* Right Section: Form wrapped in elevated glass card with in-place toggle */}
        <section className="flex items-center justify-center px-4 py-24 sm:px-6 md:px-12 lg:py-16">
          <div className="w-full max-w-[540px] rounded-3xl border border-border/80 bg-surface/80 p-8 shadow-2xl backdrop-blur-xl sm:p-10 md:p-12">
            <div className="mb-6 rounded-2xl border border-primary/20 bg-primary/10 p-4 text-center">
              <p className="text-xs text-muted mb-2">Want to jump straight into the code labs?</p>
              <Link
                href="/dashboard"
                className="inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-primary to-secondary px-4 py-2 text-xs font-semibold text-primary-foreground shadow transition hover:opacity-95"
              >
                Launch Algorithms Workbench (No Login) →
              </Link>
            </div>
            {children ? (
              children
            ) : mode === "login" ? (
              <LoginForm key="login" onToggleMode={handleToggleMode} />
            ) : (
              <RegisterForm key="register" onToggleMode={handleToggleMode} />
            )}
          </div>
        </section>
      </div>
    </div>
  );
}