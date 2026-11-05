export interface AuthUser {
  id: string;
  fullName: string;
  email: string;
  orgSlug: string;
  role: "admin" | "tenant_admin" | "platform_admin";
}

export interface Session {
  token: string;
  refreshToken?: string;
  user: AuthUser;
}