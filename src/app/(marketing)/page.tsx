import Cta from "@/features/marketing/cta";
import Faq from "@/features/marketing/faq";
import Features from "@/features/marketing/features";
import Hero from "@/features/marketing/hero";
import HowItWorks from "@/features/marketing/how-it-works";
import Marquee from "@/features/marketing/marquee";
import PipelineRing from "@/features/marketing/pipeline-ring";
import UseCases from "@/features/marketing/use-cases";

export default function Home() {
  return (
    <>
      <Hero />
      <Marquee />
      <HowItWorks />
      <UseCases />
      <PipelineRing />
      <Marquee
        flip
        className="-mt-16 md:-mt-28"
        itemsA={["Upload PDFs", "Ask anything", "See the source", "Brand it", "Go live"]}
        itemsB={["Your docs", "Your brand", "Your website", "Your answers"]}
        srText="Upload PDFs, brand your chat and go live on your website."
      />
      <Features />
      <Faq />
      <Cta />
    </>
  );
}