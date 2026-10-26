"use client";

import { useRef } from "react";
import gsap from "gsap";
import { TextPlugin } from "gsap/TextPlugin";
import { useGSAP } from "@gsap/react";
import { SendHorizontal } from "lucide-react";

gsap.registerPlugin(useGSAP, TextPlugin);

const QUESTION = "What is your refund policy?";
const ANSWER = "Refunds can be requested within the window described in your policy document.";

export default function HeroChat() {
  const root = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(prefers-reduced-motion: no-preference)", () => {
        const tl = gsap.timeline({ repeat: -1, repeatDelay: 3, defaults: { ease: "power3.out" } });
        tl.from(".hc-greeting", { opacity: 0, y: 14, duration: 0.5 })
          .from(".hc-user", { opacity: 0, y: 14, duration: 0.4 }, "+=0.5")
          .fromTo(".hc-q", { text: "" }, { text: QUESTION, duration: 1.2, ease: "none" }, "<")
          .fromTo(".hc-typing", { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.2 }, "+=0.3")
          .to(".hc-dot", { y: -4, duration: 0.3, stagger: 0.12, repeat: 3, yoyo: true })
          .to(".hc-typing", { autoAlpha: 0, duration: 0.15 })
          .from(".hc-answer", { autoAlpha: 0, duration: 0.2 }, "<")
          .fromTo(".hc-a", { text: "" }, { text: ANSWER, duration: 2, ease: "none" })
          .from(".hc-cite", { opacity: 0, scale: 0.8, duration: 0.4 }, "+=0.1");
      });
      return () => mm.revert();
    },
    { scope: root }
  );

  return (
    <div ref={root} className="float-slow w-full max-w-sm">
      <div className="overflow-hidden rounded-2xl bg-white text-slate-800 shadow-2xl ring-1 ring-black/5">
        <div className="flex items-center gap-3 px-4 py-3 text-white" style={{ background: "#4f46e5" }}>
          <span className="h-2.5 w-2.5 rounded-full bg-cyan-300" />
          <span className="text-sm font-semibold">Product Docs</span>
        </div>

        <div className="space-y-3 p-4 text-sm">
          <div className="hc-greeting max-w-[85%] rounded-2xl rounded-tl-sm bg-slate-100 px-3 py-2">
            Hi! Ask me anything about your documents.
          </div>

          <div
            className="hc-user ml-auto max-w-[85%] rounded-2xl rounded-tr-sm px-3 py-2 text-white"
            style={{ background: "#4f46e5" }}
          >
            <span className="hc-q">{QUESTION}</span>
          </div>

          <div className="relative">
            <div className="hc-typing absolute left-0 top-0 flex gap-1 rounded-2xl rounded-tl-sm bg-slate-100 px-3 py-3 opacity-0">
              <span className="hc-dot h-1.5 w-1.5 rounded-full bg-slate-400" />
              <span className="hc-dot h-1.5 w-1.5 rounded-full bg-slate-400" />
              <span className="hc-dot h-1.5 w-1.5 rounded-full bg-slate-400" />
            </div>
            <div className="hc-answer max-w-[92%] rounded-2xl rounded-tl-sm bg-slate-100 px-3 py-2">
              <p className="hc-a">{ANSWER}</p>
              <span className="hc-cite mt-2 inline-block rounded-full bg-white px-2 py-1 font-mono text-[10px] text-slate-600">
                Refund-policy.pdf · p. 2
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 text-xs text-slate-400">
          Ask a question...
          <SendHorizontal size={16} />
        </div>
      </div>
    </div>
  );
}