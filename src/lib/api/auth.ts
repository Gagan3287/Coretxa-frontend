import { apiClient, ApiError } from "./client";
import { setSession } from "@/lib/auth/session";
import type { Session } from "@/types/auth";

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
  phone: string;
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

interface BackendTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface BackendUserMeResponse {
  id: string;
  full_name: string | null;
  email: string;
  tenant_slug: string | null;
  tenant_id: string | null;
  role: string;
}

export async function login(input: LoginInput): Promise<Session> {
  try {
    const tokenResp = await apiClient<BackendTokenResponse>("/auth/login", {
      method: "POST",
      skipAuth: true,
      body: {
        tenant_slug: input.orgSlug.trim(),
        email: input.email.trim(),
        password: input.password,
      },
    });

    const me = await apiClient<BackendUserMeResponse>("/auth/me", {
      method: "GET",
      headers: {
        Authorization: `Bearer ${tokenResp.access_token}`,
      },
    });

    const session: Session = {
      token: tokenResp.access_token,
      refreshToken: tokenResp.refresh_token,
      user: {
        id: me.id,
        fullName: me.full_name || input.email.split("@")[0],
        email: me.email,
        orgSlug: me.tenant_slug || input.orgSlug.trim(),
        role: (me.role === "platform_admin" ? "platform_admin" : "tenant_admin") as Session["user"]["role"],
      },
    };

    setSession(session);
    return session;
  } catch (err: unknown) {
    if (err instanceof ApiError) {
      if (err.status === 401) {
        throw new AuthError("Incorrect organization, email or password.");
      }
      throw new AuthError(err.message);
    }
    throw new AuthError(err instanceof Error ? err.message : "Failed to log in. Please try again.");
  }
}

export async function registerOrganization(input: RegisterInput): Promise<Session> {
  try {
    const tokenResp = await apiClient<BackendTokenResponse>("/auth/register", {
      method: "POST",
      skipAuth: true,
      body: {
        full_name: input.fullName.trim(),
        org_name: input.orgName.trim(),
        org_slug: input.orgSlug.toLowerCase().trim(),
        email: input.email.trim(),
        phone: input.phone.trim().replace(/[\s\-()]/g, ""),
        password: input.password,
      },
    });

    const me = await apiClient<BackendUserMeResponse>("/auth/me", {
      method: "GET",
      headers: {
        Authorization: `Bearer ${tokenResp.access_token}`,
      },
    });

    const session: Session = {
      token: tokenResp.access_token,
      refreshToken: tokenResp.refresh_token,
      user: {
        id: me.id,
        fullName: me.full_name || input.fullName.trim(),
        email: me.email,
        orgSlug: me.tenant_slug || input.orgSlug.trim(),
        role: (me.role === "platform_admin" ? "platform_admin" : "tenant_admin") as Session["user"]["role"],
      },
    };

    setSession(session);
    return session;
  } catch (err: unknown) {
    if (err instanceof ApiError) {
      const msg = err.message.toLowerCase();
      if (err.status === 409 || msg.includes("already taken") || msg.includes("in use")) {
        throw new AuthError("That organization address is already taken.", "slug");
      }
      if (msg.includes("reserved")) {
        throw new AuthError("That organization address is reserved. Please choose another.", "slug");
      }
      throw new AuthError(err.message);
    }
    throw new AuthError(err instanceof Error ? err.message : "Registration failed. Please try again.");
  }
}