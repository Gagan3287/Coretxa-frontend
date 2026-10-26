"use client";

import { useState } from "react";
import Link from "next/link";
import MagneticButton from "@/components/ui/magnetic-button";
import { login } from "@/lib/api/auth";
import { setSession } from "@/lib/auth/session";
import { anton } from "@/lib/fonts";
import { navigateWithTransition } from "@/lib/utils/navigate";
import FieldInput from "./field-input";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type Errors = Partial<Record<"orgSlug" | "email" | "password", string>>;

export default function LoginForm() {
  const [orgSlug, setOrgSlug] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState("");
  const [loading, setLoading] = useState(false);

  const clear = (key: keyof Errors) => {
    if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }));
    if (formError) setFormError("");
  };

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;
    const next: Errors = {};
    if (orgSlug.trim().length < 2) next.orgSlug = "Enter your organization address.";
    if (!EMAIL_RE.test(email.trim())) next.email = "Enter a valid email address.";
    if (!password) next.password = "Enter your password.";
    setErrors(next);
    setFormError("");
    if (Object.keys(next).length) return;

    setLoading(true);
    try {
      const session = await login({ orgSlug: orgSlug.trim().toLowerCase(), email, password });
      setSession(session);
      navigateWithTransition("/dashboard");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
      setLoading(false);
    }
  }

  return (
    <div>
      <Link href="/" className="auth-reveal inline-block font-display text-2xl font-bold tracking-tight">
        Cortex<span className="gradient-text">a</span>
      </Link>

      <h1
        className={`${anton.className} auth-reveal mt-8 text-[clamp(2.6rem,5vw,4.2rem)] uppercase leading-none tracking-[0.01em]`}
      >
        Welcome back
      </h1>
      <p className="auth-reveal mt-4 text-sm text-muted">Sign in to manage your assistants.</p>

      <form onSubmit={submit} noValidate className="mt-10 flex flex-col gap-5">
        <FieldInput
          label="Organization address"
          value={orgSlug}
          onChange={(v) => {
            setOrgSlug(v);
            clear("orgSlug");
          }}
          placeholder="acme"
          autoComplete="organization"
          error={errors.orgSlug}
          disabled={loading}
          autoFocus
        />
        <FieldInput
          label="Email"
          type="email"
          value={email}
          onChange={(v) => {
            setEmail(v);
            clear("email");
          }}
          placeholder="you@company.com"
          autoComplete="email"
          error={errors.email}
          disabled={loading}
        />
        <FieldInput
          label="Password"
          type="password"
          value={password}
          onChange={(v) => {
            setPassword(v);
            clear("password");
          }}
          placeholder="••••••••"
          autoComplete="current-password"
          error={errors.password}
          disabled={loading}
        />

        {formError && (
          <p role="alert" className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {formError}
          </p>
        )}

        <div className="auth-reveal">
          <MagneticButton
            type="submit"
            disabled={loading}
            className={`${anton.className} w-full rounded-full bg-primary px-8 py-5 text-lg uppercase tracking-[0.12em] text-primary-foreground transition-opacity disabled:opacity-60`}
          >
            {loading ? "Signing in..." : "Sign in →"}
          </MagneticButton>
        </div>

        <p className="auth-reveal text-center text-sm text-muted">
          New to Cortexa?{" "}
          <Link href="/register" className="text-secondary underline-offset-4 hover:underline">
            Create an account
          </Link>
        </p>
        <p className="auth-reveal text-center font-mono text-[11px] tracking-wider text-muted/70">
          DEMO MODE · NO BACKEND CONNECTED YET
        </p>
      </form>
    </div>
  );
}