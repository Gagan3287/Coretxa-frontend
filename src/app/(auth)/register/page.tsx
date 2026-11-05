import type { Metadata } from "next";
import AuthShell from "@/features/auth/auth-shell";

export const metadata: Metadata = { title: "Create account | Cortexa" };

export default function RegisterPage() {
  return <AuthShell initialMode="register" />;
}