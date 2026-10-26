import CursorTrail from "@/components/effects/cursor-trail";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <style>{`html{scrollbar-width:none}html::-webkit-scrollbar{display:none}`}</style>
      <CursorTrail />
      {children}
    </>
  );
}