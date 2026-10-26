import CursorTrail from "@/components/effects/cursor-trail";
import IntroLoader from "@/components/effects/intro-loader";
import ScrollRefresh from "@/components/providers/scroll-refresh";
import Footer from "@/features/marketing/footer";
import MarketingNav from "@/features/marketing/marketing-nav";

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <style>{`html{scrollbar-width:none}html::-webkit-scrollbar{display:none}`}</style>
      <IntroLoader />
      <ScrollRefresh />
      <CursorTrail />
      <MarketingNav />
      <main>{children}</main>
      <Footer />
    </>
  );
}