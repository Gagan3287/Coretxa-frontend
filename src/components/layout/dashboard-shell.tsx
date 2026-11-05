"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Activity,
  Bot,
  Code,
  CreditCard,
  FileText,
  Gauge,
  LayoutDashboard,
  LogOut,
  Menu,
  ScrollText,
  Settings,
  Terminal,
  X,
} from "lucide-react";
import Skeleton from "@/components/ui/skeleton";
import ThemeToggle from "./theme-toggle";
import { apiClient } from "@/lib/api/client";
import { clearSession, getSession, setSession } from "@/lib/auth/session";
import type { AuthUser } from "@/types/auth";

interface BackendUserMeResponse {
  id: string;
  full_name: string | null;
  email: string;
  tenant_slug: string | null;
  tenant_id: string | null;
  role: string;
}

const nav = [
  { href: "/dashboard", label: "Workbench & Labs", icon: Terminal },
  { href: "/dashboard/bots", label: "Bots", icon: Bot },
  { href: "/dashboard/documents", label: "Documents", icon: FileText },
  { href: "/dashboard/widget", label: "Widget & Embed", icon: Code },
  { href: "/dashboard/analytics", label: "Analytics", icon: Activity },
  { href: "/dashboard/usage", label: "Usage & Limits", icon: Gauge },
  { href: "/dashboard/audit", label: "Audit Log", icon: ScrollText },
  { href: "/pricing", label: "Pricing & Plans", icon: CreditCard },
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
  const [isChecking, setIsChecking] = useState(true);
  const [userProfile, setUserProfile] = useState<AuthUser | null>(null);
  const pathname = usePathname();
  const router = useRouter();

  const [reloadCount, setReloadCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const session = getSession();
    if (!session?.token) {
      clearSession();
      const next = encodeURIComponent(pathname || "/dashboard");
      router.replace(`/login?next=${next}`);
      return;
    }

    apiClient<BackendUserMeResponse>("/auth/me")
      .then((me) => {
        if (cancelled) return;
        const updatedUser: AuthUser = {
          id: me.id,
          fullName: me.full_name || session.user?.fullName || me.email.split("@")[0],
          email: me.email,
          orgSlug: me.tenant_slug || session.user?.orgSlug || "",
          role: (me.role === "platform_admin" ? "platform_admin" : "tenant_admin") as AuthUser["role"],
        };
        setSession({ ...session, user: updatedUser });
        setUserProfile(updatedUser);
        setIsChecking(false);
      })
      .catch(() => {
        if (cancelled) return;
        clearSession();
        const next = encodeURIComponent(pathname || "/dashboard");
        router.replace(`/login?next=${next}`);
      });

    return () => {
      cancelled = true;
    };
  }, [pathname, router, reloadCount]);

  // Re-verify if restored from browser bfcache (Back/Forward navigation)
  useEffect(() => {
    const onPageShow = (e: PageTransitionEvent) => {
      if (e.persisted) {
        setReloadCount((c) => c + 1);
      }
    };
    window.addEventListener("pageshow", onPageShow);
    return () => window.removeEventListener("pageshow", onPageShow);
  }, []);

  function handleLogout() {
    clearSession();
    router.replace("/login");
  }

  // Show clean skeleton while verifying — NEVER flash protected content
  if (isChecking) {
    return (
      <div className="min-h-screen bg-background">
        <div className="flex h-16 items-center justify-between border-b border-border px-6">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-8 w-24 rounded-full" />
        </div>
        <div className="p-8 space-y-6 max-w-5xl mx-auto">
          <Skeleton className="h-10 w-48" />
          <div className="grid gap-6 md:grid-cols-3">
            <Skeleton className="h-32 rounded-2xl" />
            <Skeleton className="h-32 rounded-2xl" />
            <Skeleton className="h-32 rounded-2xl" />
          </div>
        </div>
      </div>
    );
  }

  const initials = (userProfile?.fullName || userProfile?.email || "CX")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col justify-between border-r border-border bg-surface md:flex">
        <div>
          <div className="flex h-16 items-center px-6">
            <Logo />
          </div>
          <NavLinks />
        </div>

        <div className="border-t border-border p-4">
          <div className="mb-3 px-2">
            <p className="truncate text-sm font-semibold text-foreground">
              {userProfile?.fullName || "User"}
            </p>
            <p className="truncate font-mono text-xs text-muted">
              {userProfile?.orgSlug ? `@${userProfile.orgSlug}` : userProfile?.email || ""}
            </p>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-red-400 transition hover:bg-red-500/10"
          >
            <LogOut size={16} />
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      {open && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 flex h-full w-64 flex-col justify-between border-r border-border bg-surface">
            <div>
              <div className="flex h-16 items-center justify-between px-6">
                <Logo />
                <button onClick={() => setOpen(false)} aria-label="Close menu" className="text-muted">
                  <X size={20} />
                </button>
              </div>
              <NavLinks onNavigate={() => setOpen(false)} />
            </div>

            <div className="border-t border-border p-4">
              <div className="mb-3 px-2">
                <p className="truncate text-sm font-semibold text-foreground">
                  {userProfile?.fullName || "User"}
                </p>
                <p className="truncate font-mono text-xs text-muted">
                  {userProfile?.orgSlug ? `@${userProfile.orgSlug}` : userProfile?.email || ""}
                </p>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-red-400 transition hover:bg-red-500/10"
              >
                <LogOut size={16} />
                <span>Sign out</span>
              </button>
            </div>
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
            <span className="text-sm text-muted">
              {userProfile?.orgSlug ? userProfile.orgSlug : "Organization"}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <div className="grid h-9 w-9 place-items-center rounded-full bg-primary/20 font-mono text-xs text-primary font-bold">
              {initials}
            </div>
          </div>
        </header>
        <main className="p-6 md:p-8">{children}</main>
      </div>
    </div>
  );
}