import type { Session } from "@/types/auth";

const SESSION_STORAGE_KEY = "cortexa_session";

let session: Session | null = null;

// Rehydrate on initial module evaluation in browser
if (typeof window !== "undefined") {
  try {
    const raw = window.sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (raw) {
      session = JSON.parse(raw);
    }
  } catch {
    session = null;
  }
}

export const getSession = (): Session | null => {
  if (!session && typeof window !== "undefined") {
    try {
      const raw = window.sessionStorage.getItem(SESSION_STORAGE_KEY);
      if (raw) {
        session = JSON.parse(raw);
      }
    } catch {
      session = null;
    }
  }
  return session;
};

export const setSession = (next: Session) => {
  session = next;
  if (typeof window !== "undefined") {
    try {
      window.sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(next));
    } catch {
      // Storage quota or private browsing exceptions
    }
  }
};

export const clearSession = () => {
  session = null;
  if (typeof window !== "undefined") {
    try {
      window.sessionStorage.removeItem(SESSION_STORAGE_KEY);
    } catch {
      // Ignore cleanup error
    }
  }
};