/**
 * theme.ts — light/dark theme toggle.
 *
 * - default: dark
 * - user choice persisted in localStorage as 'tower-theme' = 'light' | 'dark'
 * - applies `data-theme` on <html> (consumed by global.css)
 * - exposes a `window.towerTheme` API for the toggle button
 *
 * No dependencies, no framework. Wired through Astro's page-load event
 * so view transitions don't double-register listeners.
 */

type Theme = "light" | "dark";
const KEY = "tower-theme";
const DEFAULT: Theme = "dark";

function read(): Theme {
  if (typeof localStorage === "undefined") return DEFAULT;
  const v = localStorage.getItem(KEY);
  return v === "light" || v === "dark" ? v : DEFAULT;
}

function apply(t: Theme) {
  if (typeof document === "undefined") return;
  document.documentElement.setAttribute("data-theme", t);
  const btn = document.getElementById("theme-toggle");
  if (btn) {
    btn.setAttribute("aria-pressed", t === "light" ? "true" : "false");
    btn.textContent = t === "light" ? "☀ light" : "☾ dark";
  }
}

function toggle() {
  const cur = read();
  const next: Theme = cur === "light" ? "dark" : "light";
  if (typeof localStorage !== "undefined") {
    localStorage.setItem(KEY, next);
  }
  apply(next);
}

function init() {
  // Apply current theme (run on every page load — view transitions
  // re-execute scripts, but apply() is idempotent).
  apply(read());

  // Wire the toggle button — guard against double-binding.
  const btn = document.getElementById("theme-toggle");
  if (btn && !btn.dataset.bound) {
    btn.dataset.bound = "1";
    btn.addEventListener("click", toggle);
  }
}

// Astro view transitions fire this on every page load.
document.addEventListener("astro:page-load", init);
// Also run on first paint in case page-load already fired.
if (document.readyState !== "loading") {
  init();
}
