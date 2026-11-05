import type { Metadata } from "next";
import AuthShell from "@/features/auth/auth-shell";

export const metadata: Metadata = { title: "Sign in | Cortexa" };

export default function LoginPage() {
  return <AuthShell initialMode="login" />;
}