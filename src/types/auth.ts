export interface AuthUser {
  id: string;
  fullName: string;
  email: string;
  orgSlug: string;
  role: "admin";
}

export interface Session {
  token: string;
  user: AuthUser;
}