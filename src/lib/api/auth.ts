import type { Session } from "@/types/auth";

// MOCK: replace with real API calls once the backend's openapi.json is available.
// Test helpers: password "wrong-password" fails to log in, and the organization address
// "taken" is reported as already in use when registering.

export interface LoginInput {
  orgSlug: string;
  email: string;
  password: string;
}

export interface RegisterInput {
  fullName: string;
  orgName: string;
  orgSlug: string;
  email: string;
  password: string;
}

export class AuthError extends Error {
  field?: string;
  constructor(message: string, field?: string) {
    super(message);
    this.name = "AuthError";
    this.field = field;
  }
}

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export async function login(input: LoginInput): Promise<Session> {
  await delay(900);
  if (input.password === "wrong-password") {
    throw new AuthError("Incorrect organization, email or password.");
  }
  return {
    token: "mock-token",
    user: {
      id: "u_demo",
      fullName: "Demo Admin",
      email: input.email.trim(),
      orgSlug: input.orgSlug.trim(),
      role: "admin",
    },
  };
}

export async function registerOrganization(input: RegisterInput): Promise<Session> {
  await delay(1100);
  if (input.orgSlug === "taken") {
    throw new AuthError("That organization address is already taken.", "slug");
  }
  return {
    token: "mock-token",
    user: {
      id: "u_demo",
      fullName: input.fullName.trim(),
      email: input.email.trim(),
      orgSlug: input.orgSlug,
      role: "admin",
    },
  };
}