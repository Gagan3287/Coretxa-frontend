/**
 * Central API Client for Cortexa Backend
 * - Base URL from process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
 * - Unified FastAPI error parsing (strings or validation arrays)
 * - Automatic 401 -> token refresh -> retry once -> logout fallback
 */
import { clearSession, getSession, setSession } from "@/lib/auth/session";
import type { Session } from "@/types/auth";

export class ApiError extends Error {
  status: number;
  data?: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

interface ValidationDetailItem {
  loc?: (string | number)[];
  msg: string;
  type?: string;
}

export function parseFastApiError(data: unknown): string {
  if (!data || typeof data !== "object") return "An unexpected error occurred.";

  const record = data as Record<string, unknown>;

  if (typeof record.detail === "string") {
    return record.detail;
  }

  if (Array.isArray(record.detail)) {
    return (record.detail as ValidationDetailItem[])
      .map((item) => {
        const field = item.loc && item.loc.length > 0 ? item.loc[item.loc.length - 1] : "field";
        return `${field}: ${item.msg}`;
      })
      .join(", ");
  }

  if (typeof record.message === "string") {
    return record.message;
  }

  return "An unexpected error occurred.";
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const session = getSession();
  const refreshToken = session?.refreshToken;
  if (!refreshToken) {
    clearSession();
    return null;
  }

  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) {
      clearSession();
      if (typeof window !== "undefined") {
        // eslint-disable-next-line @next/next/no-location-assign-relative-destination
        window.location.href = "/login";
      }
      return null;
    }

    const data = (await res.json()) as { access_token: string; refresh_token: string };
    const updatedSession: Session = {
      ...session,
      token: data.access_token,
      refreshToken: data.refresh_token,
    };
    setSession(updatedSession);
    return data.access_token;
  } catch {
    clearSession();
    if (typeof window !== "undefined") {
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.href = "/login";
    }
    return null;
  } finally {
    refreshPromise = null;
  }
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
  skipAuth?: boolean;
}

export async function apiClient<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { body, params, headers = {}, skipAuth = false, ...rest } = options;

  let url = `${API_BASE}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined) searchParams.append(k, String(v));
    });
    const qs = searchParams.toString();
    if (qs) url += `?${qs}`;
  }

  const reqHeaders = new Headers(headers);

  // Auto attach Bearer token
  if (!skipAuth) {
    const session = getSession();
    if (session?.token && !reqHeaders.has("Authorization")) {
      reqHeaders.set("Authorization", `Bearer ${session.token}`);
    }
  }

  // Handle json body vs FormData
  let reqBody: BodyInit | null | undefined;
  if (body instanceof FormData || body instanceof Blob || typeof body === "string") {
    reqBody = body;
  } else if (body !== undefined && body !== null) {
    reqHeaders.set("Content-Type", "application/json");
    reqBody = JSON.stringify(body);
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...rest,
      headers: reqHeaders,
      body: reqBody,
    });
  } catch (err: unknown) {
    throw new ApiError(err instanceof Error ? err.message : "Network request failed", 0);
  }

  // 401 Auto-refresh & retry logic
  if (response.status === 401 && !skipAuth && !endpoint.startsWith("/auth/")) {
    if (!refreshPromise) {
      refreshPromise = refreshAccessToken();
    }
    const newAccessToken = await refreshPromise;

    if (newAccessToken) {
      reqHeaders.set("Authorization", `Bearer ${newAccessToken}`);
      try {
        response = await fetch(url, {
          ...rest,
          headers: reqHeaders,
          body: reqBody,
        });
      } catch (err: unknown) {
        throw new ApiError(
          err instanceof Error ? err.message : "Network request failed after token refresh",
          0
        );
      }
    } else {
      throw new ApiError("Session expired. Please log in again.", 401);
    }
  }

  if (response.status === 204) {
    return null as unknown as T;
  }

  let data: unknown = null;
  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    const errorMsg = parseFastApiError(data);
    throw new ApiError(errorMsg, response.status, data);
  }

  return data as T;
}
