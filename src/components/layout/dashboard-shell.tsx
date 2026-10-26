"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Bot, Code, FileText, Gauge, LayoutDashboard, Menu, ScrollText, Settings, X } from "lucide-react";
import ThemeToggle from "./theme-toggle";

const nav = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/bots", label: "Bots", icon: Bot },
  { href: "/dashboard/documents", label: "Documents", icon: FileText },
  { href: "/dashboard/widget", label: "Widget & Embed", icon: Code },
  { href: "/dashboard/analytics", label: "Analytics", icon: Activity },
  { href: "/dashboard/usage", label: "Usage & Limits", icon: Gauge },
  { href: "/dashboard/audit", label: "Audit Log", icon: ScrollText },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col gap-1 p-4">
      {nav.map(({ href, label, icon: Icon }) => {
        const active = href === "/dashboard" ? pathname === href : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
              active
                ? "bg-primary/15 text-primary"
                : "text-muted hover:bg-foreground/5 hover:text-foreground"
            }`}
          >
            <Icon size={18} />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

function Logo() {
  return (
    <Link href="/" className="font-display text-xl font-bold tracking-tight">
      Cortex<span className="gradient-text">a</span>
    </Link>
  );
}

export default function DashboardShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-border bg-surface md:block">
        <div className="flex h-16 items-center px-6">
          <Logo />
        </div>
        <NavLinks />
      </aside>

      {open && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-64 border-r border-border bg-surface">
            <div className="flex h-16 items-center justify-between px-6">
              <Logo />
              <button onClick={() => setOpen(false)} aria-label="Close menu" className="text-muted">
                <X size={20} />
              </button>
            </div>
            <NavLinks onNavigate={() => setOpen(false)} />
          </aside>
        </div>
      )}

      <div className="md:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-border bg-background/80 px-6 backdrop-blur">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setOpen(true)}
              aria-label="Open menu"
              className="text-muted md:hidden"
            >
              <Menu size={20} />
            </button>
            <span className="text-sm text-muted">Sample Organization</span>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <div className="grid h-9 w-9 place-items-center rounded-full bg-primary/20 font-mono text-xs text-primary">
              SO
            </div>
          </div>
        </header>
        <main className="p-6 md:p-8">{children}</main>
      </div>
    </div>
  );
}