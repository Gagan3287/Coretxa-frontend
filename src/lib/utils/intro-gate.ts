/**
 * Runs `run` once the page is allowed to start its entrance animation.
 * While an intro or a page transition is covering the screen, it waits for
 * the "cortexa:intro-done" event. Returns a cleanup function.
 */
export function whenIntroDone(run: () => void): () => void {
  const html = document.documentElement;
  if (html.dataset.intro !== "playing") {
    run();
    return () => {};
  }
  window.addEventListener("cortexa:intro-done", run, { once: true });
  return () => window.removeEventListener("cortexa:intro-done", run);
}