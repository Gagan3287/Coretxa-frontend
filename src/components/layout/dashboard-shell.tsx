"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Activity,
  Bot,
  ChevronLeft,
  ChevronRight,
  Code,
  CreditCard,
  FileText,
  Gauge,
  Home,
  LayoutDashboard,
  LogOut,
  Menu,
  ScrollText,
  Settings,
  X,
} from "lucide-react";
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
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
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
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [userProfile, setUserProfile] = useState<AuthUser>({
    id: "dev-user",
    fullName: "Cortexa Developer",
    email: "developer@cortexa.io",
    orgSlug: "cortexa-engine",
    role: "platform_admin",
  });
  const pathname = usePathname();
  const router = useRouter();

  // Load saved sidebar preference
  useEffect(() => {
    try {
      const saved = localStorage.getItem("cortexa_sidebar_collapsed");
      if (saved === "true") setIsCollapsed(true);
    } catch {}
  }, []);

  const toggleSidebar = () => {
    setIsCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("cortexa_sidebar_collapsed", String(next));
      } catch {}
      return next;
    });
  };

  // Auth gate: Require login barrier before accessing dashboard
  useEffect(() => {
    let cancelled = false;
    const session = getSession();
    if (!session?.token) {
      const target = encodeURIComponent(pathname || "/dashboard");
      router.replace(`/login?next=${target}`);
      return;
    }

    if (session.user) {
      setUserProfile(session.user);
    }
    setCheckingAuth(false);

    apiClient<BackendUserMeResponse>("/auth/me")
      .then((me) => {
        if (cancelled) return;
        const updatedUser: AuthUser = {
          id: me.id,
          fullName: me.full_name || session.user?.fullName || me.email.split("@")[0],
          email: me.email,
          orgSlug: me.tenant_slug || session.user?.orgSlug || "cortexa",
          role: (me.role === "platform_admin" ? "platform_admin" : "tenant_admin") as AuthUser["role"],
        };
        setSession({ ...session, user: updatedUser });
        setUserProfile(updatedUser);
      })
      .catch(() => {
        // If backend is offline/not reachable, gracefully retain current active profile
      });

    return () => {
      cancelled = true;
    };
  }, [pathname, router]);

  function handleReturnHome() {
    router.push("/");
  }

  function handleSignOut() {
    clearSession();
    router.replace("/login");
  }

  const initials = (userProfile.fullName || "CX").slice(0, 2).toUpperCase();

  if (checkingAuth) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <p className="font-mono text-xs text-muted">Checking authentication...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Desktop Collapsible Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-30 hidden md:flex flex-col justify-between border-r border-border bg-surface transition-all duration-300 ease-in-out ${
          isCollapsed ? "-translate-x-full w-64" : "translate-x-0 w-64"
        }`}
      >
        {/* Floating Arrow Toggle Button on the sidebar border */}
        <button
          type="button"
          onClick={toggleSidebar}
          aria-label="Collapse sidebar"
          title="Collapse sidebar"
          className="absolute -right-3.5 top-20 z-40 hidden md:flex h-7 w-7 items-center justify-center rounded-full border border-border bg-surface text-muted shadow-lg transition-transform hover:scale-110 hover:border-primary hover:text-foreground active:scale-95"
        >
          <ChevronLeft size={14} />
        </button>

        <div>
          <div className="flex h-16 items-center justify-between px-6">
            <Logo />
            <button
              type="button"
              onClick={toggleSidebar}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-border/60 bg-background/50 text-muted transition hover:bg-background hover:text-foreground active:scale-95"
              title="Collapse sidebar"
              aria-label="Collapse sidebar"
            >
              <ChevronLeft size={16} />
            </button>
          </div>
          <NavLinks />
        </div>

        <div className="border-t border-border p-4">
          <div className="mb-3 px-2">
            <p className="truncate text-sm font-semibold text-foreground">
              {userProfile.fullName}
            </p>
            <p className="truncate font-mono text-xs text-muted">
              {userProfile.orgSlug ? `@${userProfile.orgSlug}` : userProfile.email}
            </p>
          </div>
          <button
            type="button"
            onClick={handleReturnHome}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-muted transition hover:bg-foreground/5 hover:text-foreground"
          >
            <Home size={16} />
            <span>Back to Home</span>
          </button>
          <button
            type="button"
            onClick={handleSignOut}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-muted transition hover:bg-red-500/10 hover:text-red-400"
          >
            <LogOut size={16} />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Floating Edge Arrow Tab when Sidebar is Minimized/Collapsed */}
      {isCollapsed && (
        <button
          type="button"
          onClick={toggleSidebar}
          aria-label="Open sidebar"
          title="Open sidebar"
          className="fixed left-0 top-20 z-40 hidden md:flex h-10 w-8 items-center justify-center rounded-r-xl border border-l-0 border-border bg-surface/90 backdrop-blur-md text-muted shadow-2xl transition-all hover:w-9 hover:border-primary/50 hover:text-secondary active:scale-95"
        >
          <ChevronRight size={18} />
        </button>
      )}

      {/* Mobile Drawer */}
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
                  {userProfile.fullName}
                </p>
                <p className="truncate font-mono text-xs text-muted">
                  {userProfile.orgSlug ? `@${userProfile.orgSlug}` : userProfile.email}
                </p>
              </div>
              <button
                type="button"
                onClick={handleReturnHome}
                className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-muted transition hover:bg-foreground/5 hover:text-foreground"
              >
                <Home size={16} />
                <span>Back to Home</span>
              </button>
              <button
                type="button"
                onClick={handleSignOut}
                className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-muted transition hover:bg-red-500/10 hover:text-red-400"
              >
                <LogOut size={16} />
                <span>Sign Out</span>
              </button>
            </div>
          </aside>
        </div>
      )}

      {/* Main Content Area */}
      <div className={`transition-all duration-300 ease-in-out ${isCollapsed ? "md:pl-0" : "md:pl-64"}`}>
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-border bg-background/80 px-6 backdrop-blur">
          <div className="flex items-center gap-3">
            {/* Desktop Minimizer Toggle in Header */}
            <button
              type="button"
              onClick={toggleSidebar}
              aria-label={isCollapsed ? "Open sidebar" : "Collapse sidebar"}
              title={isCollapsed ? "Open sidebar" : "Collapse sidebar"}
              className="hidden md:flex items-center gap-1.5 rounded-lg border border-border/60 bg-surface/70 px-2.5 py-1.5 text-xs text-muted transition hover:border-border hover:bg-surface hover:text-foreground active:scale-95"
            >
              {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
              <span className="font-mono text-[11px]">{isCollapsed ? "Sidebar" : "Collapse"}</span>
            </button>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setOpen(true)}
              aria-label="Open menu"
              className="text-muted md:hidden"
            >
              <Menu size={20} />
            </button>
            <span className="text-sm text-muted">
              {userProfile.orgSlug}
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
