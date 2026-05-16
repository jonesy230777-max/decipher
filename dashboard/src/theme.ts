/**
 * Theme picker. HIG dark-mode pattern: light / dark / auto (follow system).
 *
 * Persistence: written to BOTH `decipher.theme` cookie (1 year) and
 * localStorage. Read order at boot is cookie -> localStorage -> "auto".
 * The synchronous bootstrap script in index.html applies the choice to
 * <html data-theme> before React mounts so navigation never causes the
 * theme to revert.
 *
 * The theme must ONLY ever be mutated from Settings -> Appearance. No
 * other page or component should call setTheme().
 */
import { useEffect, useState } from "react";

export type ThemeChoice = "light" | "dark" | "auto";

const KEY = "decipher.theme";

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
  return m ? decodeURIComponent(m[1]) : null;
}

function writeCookie(name: string, value: string) {
  if (typeof document === "undefined") return;
  // 1-year persistence, root path, SameSite=Lax for navigation safety.
  const oneYear = 60 * 60 * 24 * 365;
  document.cookie = `${name}=${encodeURIComponent(value)}; max-age=${oneYear}; path=/; SameSite=Lax`;
}

function readStored(): ThemeChoice {
  const fromCookie = readCookie(KEY);
  if (fromCookie === "light" || fromCookie === "dark" || fromCookie === "auto") return fromCookie;
  try {
    const v = localStorage.getItem(KEY);
    if (v === "light" || v === "dark" || v === "auto") return v;
  } catch { /* */ }
  return "auto";
}

export function applyTheme(t: ThemeChoice) {
  if (t === "auto") {
    document.documentElement.removeAttribute("data-theme");
  } else {
    document.documentElement.setAttribute("data-theme", t);
  }
}

/**
 * Initialise the theme. Called once from main.tsx so the choice survives
 * navigation regardless of which page mounts first. The inline script in
 * index.html already applies the attribute pre-React; this re-applies to
 * make sure nothing later clobbered it.
 */
export function initTheme() {
  applyTheme(readStored());
}

/**
 * Hook for the Settings appearance card. Reads from cookie/localStorage
 * at mount, writes both on change. No other page should use this hook.
 */
export function useTheme() {
  const [theme, setTheme] = useState<ThemeChoice>(() => readStored());
  useEffect(() => {
    applyTheme(theme);
    try { localStorage.setItem(KEY, theme); } catch { /* */ }
    writeCookie(KEY, theme);
  }, [theme]);
  return [theme, setTheme] as const;
}
