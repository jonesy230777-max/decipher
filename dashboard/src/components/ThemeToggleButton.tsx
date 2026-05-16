import { useTheme, type ThemeChoice } from "../theme";

const NEXT: Record<ThemeChoice, ThemeChoice> = {
  light: "dark",
  dark:  "auto",
  auto:  "light",
};
const GLYPH: Record<ThemeChoice, string> = {
  light: "☀︎",
  dark:  "☾",
  auto:  "◐",
};
const LABEL: Record<ThemeChoice, string> = {
  light: "Light",
  dark:  "Dark",
  auto:  "Auto",
};

export function ThemeToggleButton() {
  const [theme, setTheme] = useTheme();
  return (
    <button
      onClick={() => setTheme(NEXT[theme])}
      title={`Theme: ${LABEL[theme]} (click for ${LABEL[NEXT[theme]]})`}
      className="hig-footnote"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "var(--space-1)",
        padding: "4px 10px",
        minHeight: 28,
        border: "1px solid var(--colour-separator-opaque)",
        borderRadius: "var(--radius-sm)",
        background: "var(--colour-bg-system-secondary)",
        color: "var(--colour-label)",
        cursor: "pointer",
      }}
    >
      <span style={{ fontSize: 13 }} aria-hidden="true">{GLYPH[theme]}</span>
      <span>{LABEL[theme]}</span>
    </button>
  );
}
