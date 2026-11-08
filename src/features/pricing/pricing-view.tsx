"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Check, CheckCircle2, ChevronDown, CreditCard, RefreshCw, ShieldCheck, Sparkles } from "lucide-react";
import { anton } from "@/lib/fonts";
import { getSession } from "@/lib/auth/session";
import { PRICING_TIERS, PRICING_FAQS, type PricingTier } from "@/config/pricing";
import Dialog from "@/components/ui/dialog";

export default function PricingView() {
  const router = useRouter();
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<PricingTier | null>(null);
  const [openFaq, setOpenFaq] = useState<number | null>(0);
  const [isPaying, setIsPaying] = useState(false);
  const [paymentSuccess, setPaymentSuccess] = useState(false);
  const [isFromBotFlow, setIsFromBotFlow] = useState(false);

  useEffect(() => {
    const session = getSession();
    if (session?.token) {
      const frame = requestAnimationFrame(() => {
        setIsLoggedIn(true);
      });
      return () => cancelAnimationFrame(frame);
    }
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("flow") === "create-bot") {
        setIsFromBotFlow(true);
        // Automatically preselect the popular Pro plan for checkout
        const proPlan = PRICING_TIERS.find((t) => t.id === "pro") || PRICING_TIERS[1];
        setSelectedPlan(proPlan);
      }
    }
  }, []);

  function handlePlanClick(tier: PricingTier) {
    setSelectedPlan(tier);
    setPaymentSuccess(false);
  }

  function handleSimulatePayment() {
    if (!selectedPlan) return;
    setIsPaying(true);

    setTimeout(() => {
      setIsPaying(false);
      setPaymentSuccess(true);
      if (typeof window !== "undefined") {
        localStorage.setItem("cortexa_subscribed", "true");
        localStorage.setItem("cortexa_plan", selectedPlan.name);
      }

      // Automatically redirect back to the bot creation dashboard after 1.2s
      setTimeout(() => {
        setSelectedPlan(null);
        router.push("/dashboard/bots?create=true");
      }, 1200);
    }, 1000);
  }

  return (
    <div className="relative min-h-screen bg-background text-foreground pb-24 pt-28 md:pt-36">
      {/* Background ambient glow */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 h-[600px] overflow-hidden opacity-30"
      >
        <div className="absolute left-1/2 top-0 h-[450px] w-[900px] -translate-x-1/2 rounded-full bg-gradient-to-b from-primary/30 to-secondary/10 blur-[130px]" />
      </div>

      <div className="relative mx-auto max-w-[1400px] px-6 md:px-10">
        {/* Banner if redirected from Bot Creation flow */}
        {isFromBotFlow && (
          <div className="mx-auto mb-10 max-w-2xl rounded-2xl border border-secondary/40 bg-secondary/10 p-4 text-center">
            <p className="font-mono text-xs uppercase tracking-wider text-secondary font-semibold">
              ✨ Subscription Required To Deploy Additional Bots
            </p>
            <p className="mt-1 text-sm text-foreground/90">
              Select any plan below to simulate a demo payment and immediately unlock unlimited bot creation!
            </p>
          </div>
        )}

        {/* Header Section */}
        <div className="mx-auto max-w-3xl text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-secondary/30 bg-secondary/10 px-4 py-1.5 font-mono text-xs font-semibold tracking-wider text-secondary">
            <Sparkles size={14} />
            <span>TRANSPARENT INR PRICING</span>
          </div>

          <h1
            className={`${anton.className} mt-6 text-[clamp(2.8rem,6vw,5.2rem)] uppercase leading-[0.95] tracking-[0.01em]`}
          >
            Predictable Plans. <br />
            <span className="gradient-text">Zero Per-Message Shock.</span>
          </h1>

          <p className="mt-6 text-base text-muted sm:text-lg">
            Scale your assistant fleet by bot capacity. Upload documents, customize your widget, and
            embed everywhere with strict tenant PostgreSQL isolation.
          </p>

          <p className="mt-3 font-mono text-xs tracking-wide text-muted/70">
            All prices in INR (₹). Database isolation & vector search included on every tier.
          </p>
        </div>

        {/* Pricing Cards Grid */}
        <div className="mt-16 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {PRICING_TIERS.map((tier) => {
            const isPopular = tier.popular;
            return (
              <div
                key={tier.id}
                className={`relative flex flex-col justify-between rounded-3xl border p-8 transition-all duration-300 hover:-translate-y-1 ${
                  isPopular
                    ? "border-secondary/60 bg-surface/90 shadow-2xl shadow-secondary/10 ring-1 ring-secondary/40"
                    : "border-border/80 bg-surface/60 hover:border-border"
                }`}
              >
                {isPopular && (
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 rounded-full bg-gradient-to-r from-primary to-secondary px-4 py-1 font-mono text-[11px] font-bold uppercase tracking-wider text-primary-foreground shadow-md">
                    Most Popular
                  </div>
                )}

                <div>
                  <div className="flex items-center justify-between">
                    <h3 className="font-display text-xl font-bold tracking-tight text-foreground">
                      {tier.name}
                    </h3>
                    <span className="rounded-xl bg-primary/10 px-3 py-1 font-mono text-xs font-semibold text-primary">
                      {tier.bots === 1 ? "1 Assistant" : tier.bots > 10 ? "> 10 Assistants" : `${tier.bots} Assistants`}
                    </span>
                  </div>

                  <p className="mt-3 min-h-[40px] text-xs leading-relaxed text-muted">
                    {tier.tagline}
                  </p>

                  <div className="mt-6 border-b border-border/60 pb-6">
                    {tier.priceInr !== null ? (
                      <div className="flex items-baseline gap-1">
                        <span className="font-display text-4xl font-extrabold tracking-tight text-foreground">
                          ₹{tier.priceInr.toLocaleString("en-IN")}
                        </span>
                        <span className="text-sm font-medium text-muted">{tier.period}</span>
                      </div>
                    ) : (
                      <div className="font-display text-4xl font-extrabold tracking-tight text-foreground">
                        Custom
                      </div>
                    )}
                    {tier.perBotPrice && tier.bots > 1 && (
                      <p className="mt-1 font-mono text-xs text-secondary">
                        ₹{tier.perBotPrice.toLocaleString("en-IN")} / bot / month
                      </p>
                    )}
                  </div>

                  {/* Features list */}
                  <div className="mt-6 space-y-3">
                    <p className="font-mono text-[11px] uppercase tracking-wider text-muted">
                      What&apos;s Included:
                    </p>
                    <ul className="space-y-2.5 text-sm">
                      {tier.features.map((feature) => (
                        <li key={feature} className="flex items-start gap-2.5">
                          <Check size={16} className="mt-0.5 shrink-0 text-secondary" />
                          <span className="text-muted-foreground">{feature}</span>
                        </li>
                      ))}
                      {tier.plannedFeatures?.map((pf) => (
                        <li key={pf} className="flex items-start gap-2.5 text-muted/70">
                          <Sparkles size={16} className="mt-0.5 shrink-0 text-primary/60" />
                          <span>{pf}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* CTA Button */}
                <div className="mt-8 pt-4">
                  {tier.id === "enterprise" ? (
                    <a
                      href={tier.ctaHref}
                      className="flex w-full items-center justify-center gap-2 rounded-xl border border-border bg-foreground/5 py-3.5 text-sm font-semibold text-foreground transition-all hover:bg-foreground/10"
                    >
                      <span>{tier.ctaLabel}</span>
                      <ArrowRight size={16} />
                    </a>
                  ) : (
                    <button
                      type="button"
                      onClick={() => handlePlanClick(tier)}
                      className={`flex w-full items-center justify-center gap-2 rounded-xl py-3.5 text-sm font-semibold transition-all ${
                        isPopular
                          ? "bg-primary text-primary-foreground shadow-lg hover:opacity-90 hover:shadow-primary/20"
                          : "border border-border bg-foreground/5 text-foreground hover:bg-foreground/10"
                      }`}
                    >
                      <span>{isFromBotFlow ? "Pay & Unlock Bots" : tier.ctaLabel}</span>
                      <ArrowRight size={16} />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* FAQ Section */}
        <section className="mt-28 mx-auto max-w-3xl">
          <div className="text-center">
            <h2
              className={`${anton.className} text-[clamp(2rem,4vw,3.2rem)] uppercase tracking-[0.01em]`}
            >
              Frequently Asked Questions
            </h2>
            <p className="mt-3 text-sm text-muted">
              Everything you need to know about Cortexa plans, limits, and billing.
            </p>
          </div>

          <div className="mt-10 space-y-4">
            {PRICING_FAQS.map((faq, index) => {
              const isOpen = openFaq === index;
              return (
                <div
                  key={faq.question}
                  className="rounded-2xl border border-border/80 bg-surface/50 overflow-hidden transition"
                >
                  <button
                    type="button"
                    onClick={() => setOpenFaq(isOpen ? null : index)}
                    className="flex w-full items-center justify-between px-6 py-5 text-left text-base font-semibold text-foreground transition hover:text-secondary"
                  >
                    <span>{faq.question}</span>
                    <ChevronDown
                      size={18}
                      className={`shrink-0 transition-transform duration-200 text-muted ${
                        isOpen ? "rotate-180 text-secondary" : ""
                      }`}
                    />
                  </button>
                  {isOpen && (
                    <div className="px-6 pb-5 pt-1 text-sm leading-relaxed text-muted border-t border-border/40">
                      {faq.answer}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* Bottom CTA Banner */}
        <section className="mt-24 rounded-3xl border border-border/80 bg-gradient-to-r from-surface via-surface/80 to-surface p-10 text-center shadow-xl md:p-14">
          <h3 className={`${anton.className} text-[clamp(2.2rem,4.5vw,3.6rem)] uppercase tracking-[0.01em]`}>
            Ready to Build Your Assistant?
          </h3>
          <p className="mx-auto mt-4 max-w-xl text-sm text-muted md:text-base">
            Upload your documents, configure your assistant style, and paste the widget on your
            website in minutes.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/dashboard/bots"
              className="inline-flex items-center gap-2 rounded-full bg-primary px-8 py-3.5 text-sm font-semibold text-primary-foreground transition-transform hover:-translate-y-0.5"
            >
              <span>Go to Bots Dashboard</span>
              <ArrowRight size={16} />
            </Link>
            <Link
              href="/"
              className="inline-flex items-center gap-2 rounded-full border border-border bg-foreground/5 px-8 py-3.5 text-sm font-semibold text-foreground transition hover:bg-foreground/10"
            >
              Learn More
            </Link>
          </div>
        </section>
      </div>

      {/* Razorpay Demo Payment Modal */}
      {selectedPlan && (
        <Dialog
          open={!!selectedPlan}
          onClose={() => !isPaying && setSelectedPlan(null)}
          title={`Checkout — ${selectedPlan.name} Plan`}
        >
          <div className="space-y-5 text-sm text-muted">
            <div className="flex items-center justify-between rounded-2xl border border-primary/20 bg-primary/10 p-4 text-foreground">
              <div className="flex items-center gap-3">
                <CreditCard className="shrink-0 text-primary" size={24} />
                <div>
                  <p className="font-semibold text-base">
                    {selectedPlan.name} Subscription
                  </p>
                  <p className="text-xs text-muted">
                    Capacity for {selectedPlan.bots} active AI assistants
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="font-display text-2xl font-bold text-foreground">
                  {selectedPlan.priceInr ? `₹${selectedPlan.priceInr.toLocaleString("en-IN")}` : "Custom"}
                </p>
                <span className="font-mono text-[10px] text-muted">Billed monthly</span>
              </div>
            </div>

            {paymentSuccess ? (
              <div className="space-y-3 rounded-2xl border border-green-500/30 bg-green-500/10 p-5 text-center text-green-400">
                <CheckCircle2 size={36} className="mx-auto text-green-400" />
                <p className="font-semibold text-base">Payment Authorized Successfully!</p>
                <p className="text-xs text-green-300/80">
                  Subscription is active. Redirecting you to create your bot now...
                </p>
              </div>
            ) : (
              <>
                <div className="space-y-3 rounded-2xl border border-border bg-background/50 p-4">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted font-mono uppercase">Payment Gateway</span>
                    <span className="flex items-center gap-1 font-mono text-secondary font-semibold">
                      <ShieldCheck size={14} /> Razorpay Sandbox (Demo Mode)
                    </span>
                  </div>
                  <div className="border-t border-border/40 pt-2 text-xs space-y-1.5 text-muted">
                    <div className="flex justify-between">
                      <span>Plan Base Price</span>
                      <span>₹{selectedPlan.priceInr?.toLocaleString("en-IN") || "0"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>GST (18%)</span>
                      <span className="text-green-400">Waived for Demo</span>
                    </div>
                    <div className="flex justify-between font-bold text-foreground pt-1 border-t border-border/40">
                      <span>Total Amount Due</span>
                      <span>₹{selectedPlan.priceInr?.toLocaleString("en-IN") || "0"}</span>
                    </div>
                  </div>
                </div>

                <p className="text-xs text-muted">
                  Clicking below simulates a real payment confirmation and instantly grants your bot creation quota.
                </p>

                <div className="flex flex-col gap-2.5 sm:flex-row pt-2">
                  <button
                    type="button"
                    onClick={handleSimulatePayment}
                    disabled={isPaying}
                    className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-primary to-secondary px-5 py-3 text-center text-sm font-semibold text-primary-foreground transition hover:opacity-95 disabled:opacity-50 shadow-lg shadow-primary/20"
                  >
                    {isPaying ? (
                      <>
                        <RefreshCw size={16} className="animate-spin" />
                        <span>Processing Payment...</span>
                      </>
                    ) : (
                      <>
                        <span>Pay ₹{selectedPlan.priceInr?.toLocaleString("en-IN")} & Activate</span>
                        <ArrowRight size={16} />
                      </>
                    )}
                  </button>
                  <button
                    type="button"
                    disabled={isPaying}
                    onClick={() => setSelectedPlan(null)}
                    className="rounded-xl border border-border px-4 py-3 text-center text-sm font-medium text-muted hover:bg-foreground/5 disabled:opacity-50"
                  >
                    Cancel
                  </button>
                </div>
              </>
            )}
          </div>
        </Dialog>
      )}
    </div>
  );
}
