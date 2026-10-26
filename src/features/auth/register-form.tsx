"use client";

import { useState } from "react";
import Link from "next/link";
import MagneticButton from "@/components/ui/magnetic-button";
import { AuthError, registerOrganization } from "@/lib/api/auth";
import { setSession } from "@/lib/auth/session";
import { anton } from "@/lib/fonts";
import { navigateWithTransition } from "@/lib/utils/navigate";
import FieldInput from "./field-input";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const SLUG_RE = /^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$/;

const slugify = (value: string) =>
  value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 32);

type Errors = Partial<Record<"fullName" | "orgName" | "slug" | "email" | "password", string>>;

export default function RegisterForm() {
  const [fullName, setFullName] = useState("");
  const [orgName, setOrgName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState("");
  const [loading, setLoading] = useState(false);

  const clear = (key: keyof Errors) => {
    if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }));
    if (formError) setFormError("");
  };

  function validate(): Errors {
    const next: Errors = {};
    if (fullName.trim().length < 2) next.fullName = "Enter your full name.";
    if (orgName.trim().length < 2) next.orgName = "Enter your organization name.";
    if (!SLUG_RE.test(slug)) next.slug = "Use 3 to 32 lowercase letters, numbers or hyphens.";
    if (!EMAIL_RE.test(email.trim())) next.email = "Enter a valid email address.";
    if (password.length < 8) next.password = "Use at least 8 characters.";
    return next;
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;
    const found = validate();
    setErrors(found);
    setFormError("");
    if (Object.keys(found).length) return;

    setLoading(true);
    try {
      const session = await registerOrganization({ fullName, orgName: orgName.trim(), orgSlug: slug, email, password });
      setSession(session);
      navigateWithTransition("/dashboard");
    } catch (err) {
      if (err instanceof AuthError && err.field === "slug") {
        setErrors({ slug: err.message });
      } else {
        setFormError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
      }
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
        Create account
      </h1>
      <p className="auth-reveal mt-4 text-sm text-muted">
        Set up your organization and build your first assistant.
      </p>

      <form onSubmit={submit} noValidate className="mt-10 flex flex-col gap-5">
        <FieldInput
          label="Full name"
          value={fullName}
          onChange={(v) => {
            setFullName(v);
            clear("fullName");
          }}
          placeholder="Your name"
          autoComplete="name"
          error={errors.fullName}
          disabled={loading}
          autoFocus
        />
        <FieldInput
          label="Organization name"
          value={orgName}
          onChange={(v) => {
            setOrgName(v);
            clear("orgName");
            if (!slugTouched) {
              setSlug(slugify(v));
              clear("slug");
            }
          }}
          placeholder="Acme Inc."
          autoComplete="organization"
          error={errors.orgName}
          disabled={loading}
        />
        <FieldInput
          label="Organization address"
          value={slug}
          onChange={(v) => {
            setSlugTouched(true);
            setSlug(slugify(v));
            clear("slug");
          }}
          placeholder="acme"
          hint="You will use this to sign in."
          error={errors.slug}
          disabled={loading}
        />
        <FieldInput
          label="Work email"
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
          autoComplete="new-password"
          hint="At least 8 characters."
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
            {loading ? "Creating..." : "Create account →"}
          </MagneticButton>
        </div>

        <p className="auth-reveal text-center text-sm text-muted">
          Already have an account?{" "}
          <Link href="/login" className="text-secondary underline-offset-4 hover:underline">
            Sign in
          </Link>
        </p>
        <p className="auth-reveal text-center font-mono text-[11px] tracking-wider text-muted/70">
          DEMO MODE · NO BACKEND CONNECTED YET
        </p>
      </form>
    </div>
  );
}