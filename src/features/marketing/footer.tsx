import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-8 px-6 py-12 md:flex-row md:items-center md:justify-between md:px-8">
        <div>
          <Link href="/" className="font-display text-xl font-bold tracking-tight">
            Cortex<span className="gradient-text">a</span>
          </Link>
          <p className="mt-2 text-sm text-muted">AI assistants trained on your documents.</p>
        </div>
        <nav className="flex flex-wrap gap-6 text-sm text-muted" aria-label="Footer">
          <a href="#how" className="hover:text-foreground">How it works</a>
          <a href="#use-cases" className="hover:text-foreground">Use cases</a>
          <a href="#features" className="hover:text-foreground">Features</a>
          <a href="#faq" className="hover:text-foreground">FAQ</a>
          <Link href="/pricing" className="hover:text-foreground">Pricing</Link>
          <Link href="/dashboard" className="hover:text-foreground">Dashboard</Link>
        </nav>
      </div>
      <p className="px-6 pb-8 text-xs text-muted md:px-8">© {new Date().getFullYear()} Cortexa</p>
    </footer>
  );
}