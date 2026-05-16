/**
 * Theme picker. HIG dark-mode pattern: light / dark / auto (follow system).
 * Persists in localStorage, applies via [data-theme] on <html>.
 */
import { useEffect, useState } from "react";

export type ThemeChoice = "light" | "dark" | "auto";

const KEY = "decipher.theme";

export function applyTheme(t: ThemeChoice) {
  if (t === "auto") {
    document.documentElement.removeAttribute("data-theme");
  } else {
    document.documentElement.setAttribute("data-theme", t);
  }
}

export function useTheme() {
  const [theme, setTheme] = useState<ThemeChoice>(() => {
    const v = (typeof localStorage !== "undefined" && localStorage.getItem(KEY)) as ThemeChoice | null;
    return v ?? "auto";
  });
  useEffect(() => {
    applyTheme(theme);
    try { localStorage.setItem(KEY, theme); } catch { /* ignore */ }
  }, [theme]);
  return [theme, setTheme] as const;
}
