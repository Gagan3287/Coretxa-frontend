export const NAVIGATE_EVENT = "cortexa:navigate";

/** Navigate from code with the page transition. */
export function navigateWithTransition(href: string) {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent<string>(NAVIGATE_EVENT, { detail: href }));
  }
}

/**
 * Sanitizes a redirect path to ensure it is strictly a safe internal application route.
 * Rejects external origins, protocol-relative paths (//), backslash bypasses, and protocols.
 */
export function sanitizeNextPath(raw: string | null | undefined, fallback = "/dashboard"): string {
  if (!raw || typeof raw !== "string") return fallback;
  const trimmed = raw.trim();
  // Must start with a single slash, not double slash, and not contain backslash or protocol
  if (!trimmed.startsWith("/") || trimmed.startsWith("//") || trimmed.includes("\\")) {
    return fallback;
  }
  // Disallow any scheme before a question mark or hash (e.g., /test:alert(1))
  const pathPart = trimmed.split(/[?#]/)[0];
  if (pathPart.includes(":")) {
    return fallback;
  }
  return trimmed;
}