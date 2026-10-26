import type { Metadata } from "next";
import AuthShell from "@/features/auth/auth-shell";
import RegisterForm from "@/features/auth/register-form";

export const metadata: Metadata = { title: "Create account | Cortexa" };

export default function RegisterPage() {
  return (
    <AuthShell
      tagline={["Build.", "Brand.", "Deploy."]}
      description="Create your organization, upload your documents and put an assistant on your website."
    >
      <RegisterForm />
    </AuthShell>
  );
}