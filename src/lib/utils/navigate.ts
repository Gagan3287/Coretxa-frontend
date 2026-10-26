export const NAVIGATE_EVENT = "cortexa:navigate";

/** Navigate from code (for example after a login) with the blue-lines page transition. */
export function navigateWithTransition(href: string) {
  window.dispatchEvent(new CustomEvent<string>(NAVIGATE_EVENT, { detail: href }));
}