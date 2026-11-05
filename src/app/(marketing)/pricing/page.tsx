import type { Metadata } from "next";
import PricingView from "@/features/pricing/pricing-view";

export const metadata: Metadata = {
  title: "Pricing & Plans | Cortexa",
  description:
    "Transparent, per-assistant pricing in INR. Build, brand, and deploy custom AI assistants with document ingestion and embeddable widgets.",
};

export default function PricingPage() {
  return <PricingView />;
}
