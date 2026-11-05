"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Check, ChevronDown, CreditCard, Sparkles } from "lucide-react";
import { anton } from "@/lib/fonts";
import { getSession } from "@/lib/auth/session";
import { PRICING_TIERS, PRICING_FAQS, type PricingTier } from "@/config/pricing";
import Dialog from "@/components/ui/dialog";

export default function PricingView() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<PricingTier | null>(null);
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  useEffect(() => {
    const session = getSession();
    if (session?.token) {
      const frame = requestAnimationFrame(() => {
        setIsLoggedIn(true);
      });
      return () => cancelAnimationFrame(frame);
    }
  }, []);

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
                  ) : isLoggedIn ? (
                    <button
                      type="button"
                      onClick={() => setSelectedPlan(tier)}
                      className={`flex w-full items-center justify-center gap-2 rounded-xl py-3.5 text-sm font-semibold transition-all ${
                        isPopular
                          ? "bg-primary text-primary-foreground shadow-lg hover:opacity-90 hover:shadow-primary/20"
                          : "border border-border bg-foreground/5 text-foreground hover:bg-foreground/10"
                      }`}
                    >
                      <span>{tier.ctaLabel}</span>
                      <ArrowRight size={16} />
                    </button>
                  ) : (
                    <Link
                      href={tier.ctaHref}
                      className={`flex w-full items-center justify-center gap-2 rounded-xl py-3.5 text-sm font-semibold transition-all ${
                        isPopular
                          ? "bg-primary text-primary-foreground shadow-lg hover:opacity-90 hover:shadow-primary/20"
                          : "border border-border bg-foreground/5 text-foreground hover:bg-foreground/10"
                      }`}
                    >
                      <span>{tier.ctaLabel}</span>
                      <ArrowRight size={16} />
                    </Link>
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
              href={isLoggedIn ? "/dashboard" : "/register"}
              className="inline-flex items-center gap-2 rounded-full bg-primary px-8 py-3.5 text-sm font-semibold text-primary-foreground transition-transform hover:-translate-y-0.5"
            >
              <span>{isLoggedIn ? "Go to Dashboard" : "Get Started Now"}</span>
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

      {/* Logged-In Plan Change Modal */}
      {selectedPlan && (
        <Dialog
          open={!!selectedPlan}
          onClose={() => setSelectedPlan(null)}
          title={`Plan Request: ${selectedPlan.name}`}
        >
          <div className="space-y-4 text-sm text-muted">
            <div className="flex items-center gap-3 rounded-xl bg-primary/10 p-3.5 text-foreground">
              <CreditCard className="shrink-0 text-primary" size={20} />
              <div>
                <p className="font-semibold text-sm">
                  {selectedPlan.name} Plan ({selectedPlan.bots} Bots)
                </p>
                <p className="text-xs text-muted">
                  {selectedPlan.priceInr ? `₹${selectedPlan.priceInr.toLocaleString("en-IN")}/month` : "Custom"}
                </p>
              </div>
            </div>

            <p className="leading-relaxed">
              You are currently logged into an active organization. In-dashboard self-serve card and
              UPI upgrades are launching soon.
            </p>

            <p className="leading-relaxed">
              To immediately increase your assistant quota to{" "}
              <strong className="text-foreground">{selectedPlan.bots} bots</strong>, our operations
              team will update your tenant tier directly upon request.
            </p>

            <div className="mt-6 flex flex-col gap-2.5 sm:flex-row">
              <a
                href={`mailto:support@cortexa.io?subject=Upgrade%20to%20${encodeURIComponent(
                  selectedPlan.name
                )}%20Plan`}
                className="flex-1 rounded-xl bg-primary px-4 py-2.5 text-center text-sm font-semibold text-primary-foreground transition hover:opacity-90"
              >
                Email Support to Upgrade
              </a>
              <button
                type="button"
                onClick={() => setSelectedPlan(null)}
                className="rounded-xl border border-border px-4 py-2.5 text-center text-sm font-medium text-muted hover:bg-foreground/5"
              >
                Close
              </button>
            </div>
          </div>
        </Dialog>
      )}
    </div>
  );
}
