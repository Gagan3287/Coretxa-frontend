import type { Metadata } from "next";
import AuthShell from "@/features/auth/auth-shell";
import LoginForm from "@/features/auth/login-form";

export const metadata: Metadata = { title: "Sign in | Cortexa" };

export default function LoginPage() {
  return (
    <AuthShell
      tagline={["Welcome.", "Back to", "Cortexa."]}
      description="Pick up where you left off: your documents, your bots and your widget."
    >
      <LoginForm />
    </AuthShell>
  );
}