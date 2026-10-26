import type { Session } from "@/types/auth";

// The access token lives in memory only. It is never written to localStorage or cookies.
// A refresh or a closed tab clears it, which matches the planned behavior (no refresh endpoint).
let session: Session | null = null;

export const getSession = () => session;
export const setSession = (next: Session) => {
  session = next;
};
export const clearSession = () => {
  session = null;
};