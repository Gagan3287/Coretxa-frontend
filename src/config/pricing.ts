export interface PricingTier {
  id: string;
  name: string;
  bots: number;
  priceInr: number | null;
  period: string;
  perBotPrice?: number;
  tagline: string;
  popular?: boolean;
  features: string[];
  plannedFeatures?: string[];
  ctaLabel: string;
  ctaHref: string;
}

export const PRICING_TIERS: PricingTier[] = [
  {
    id: "starter",
    name: "Starter",
    bots: 1,
    priceInr: 1000,
    period: "/month",
    perBotPrice: 1000,
    tagline: "Ideal for a single product assistant or documentation bot.",
    features: [
      "1 AI Assistant bot",
      "PDF document upload & parsing",
      "Vector embeddings & semantic retrieval",
      "Custom branded web chat widget",
      "Unique widget API key & embed snippet",
      "Audit logging & usage metrics",
      "Tenant database isolation (RLS)",
    ],
    plannedFeatures: ["Direct in-app card billing (coming soon)"],
    ctaLabel: "Get Started",
    ctaHref: "/register?plan=starter",
  },
  {
    id: "growth-2",
    name: "Growth Duo",
    bots: 2,
    priceInr: 1800,
    period: "/month",
    perBotPrice: 900,
    tagline: "Separate support and knowledge assistants for small teams.",
    features: [
      "2 AI Assistant bots",
      "PDF document upload per bot",
      "Independent vector index per bot",
      "Custom branded web chat widget",
      "Unique widget API keys per bot",
      "Audit logging & usage metrics",
      "Tenant database isolation (RLS)",
    ],
    plannedFeatures: ["Automated doc re-sync (coming soon)"],
    ctaLabel: "Get Started",
    ctaHref: "/register?plan=growth-2",
  },
  {
    id: "growth-3",
    name: "Growth Trio",
    bots: 3,
    priceInr: 2500,
    period: "/month",
    perBotPrice: 833,
    tagline: "Multi-assistant setup for sales, support, and internal ops.",
    features: [
      "3 AI Assistant bots",
      "PDF document upload per bot",
      "Independent vector index per bot",
      "Custom branded web chat widget",
      "Unique widget API keys per bot",
      "Audit logging & usage metrics",
      "Tenant database isolation (RLS)",
    ],
    plannedFeatures: ["Automated doc re-sync (coming soon)"],
    ctaLabel: "Get Started",
    ctaHref: "/register?plan=growth-3",
  },
  {
    id: "pro",
    name: "Pro 5",
    bots: 5,
    priceInr: 3800,
    period: "/month",
    perBotPrice: 760,
    popular: true,
    tagline: "Our most popular tier for full multi-department coverage.",
    features: [
      "5 AI Assistant bots",
      "Full PDF document ingestion & chunking",
      "Independent vector index per bot",
      "Custom widget themes & branding",
      "Unique widget API keys per bot",
      "Comprehensive audit logs & metrics",
      "Strict PostgreSQL RLS tenant isolation",
      "Priority embedding generation",
    ],
    plannedFeatures: ["Custom domain CNAMEs (coming soon)"],
    ctaLabel: "Start Pro Plan",
    ctaHref: "/register?plan=pro",
  },
  {
    id: "scale",
    name: "Scale 10",
    bots: 10,
    priceInr: 7000,
    period: "/month",
    perBotPrice: 700,
    tagline: "Designed for SaaS platforms and agencies managing multiple bots.",
    features: [
      "10 AI Assistant bots",
      "High-volume document ingestion",
      "Independent vector index per bot",
      "Custom branding & white-label ready",
      "Unique widget API keys per bot",
      "Full audit logs & usage tracking",
      "Strict PostgreSQL RLS tenant isolation",
      "Dedicated tenant schema guard",
    ],
    plannedFeatures: ["Multi-format doc sync (coming soon)"],
    ctaLabel: "Scale With 10 Bots",
    ctaHref: "/register?plan=scale",
  },
  {
    id: "enterprise",
    name: "Enterprise",
    bots: 11,
    priceInr: null,
    period: "Custom",
    tagline: "Custom scale, dedicated capacity, and tailored deployment.",
    features: [
      "More than 10 AI Assistant bots",
      "Custom document volume allowances",
      "Dedicated infrastructure & SLAs",
      "Custom LLM & embedding model routing",
      "Full widget white-labeling",
      "Enterprise security review & audit access",
      "Direct engineer support channel",
    ],
    ctaLabel: "Contact Us",
    ctaHref: "mailto:support@cortexa.io?subject=Cortexa%20Enterprise%20Plan",
  },
];

export const PRICING_FAQS = [
  {
    question: "What counts as an assistant / bot?",
    answer:
      "Each bot has its own distinct knowledge base, document versions, widget configuration, and unique widget API key. You can deploy different bots to different pages or websites.",
  },
  {
    question: "Can I upgrade or change my plan later?",
    answer:
      "Yes. You can upgrade your plan at any time. When upgraded, your bot limit increases immediately in your dashboard.",
  },
  {
    question: "How are payments handled?",
    answer:
      "All pricing is quoted in INR (Indian Rupees). Automated online payment gateway integrations are currently in progress; subscriptions are invoiced directly upon registration.",
  },
  {
    question: "What document formats and limits are supported?",
    answer:
      "Cortexa supports PDF document uploads up to 10MB per file. Documents are parsed, split into intelligent chunks, and embedded into vector search representations.",
  },
  {
    question: "Is my organization data kept private and secure?",
    answer:
      "Yes. Cortexa enforces strict multi-tenant Row Level Security (RLS) at the PostgreSQL database layer. No organization can access or query another organization's documents or assistants.",
  },
];
