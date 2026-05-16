import type { Bootstrap } from "../api";
import { Card } from "../components/Card";
import { useTheme, type ThemeChoice } from "../theme";

export default function Settings({ boot }: { boot: Bootstrap | null }) {
  const [theme, setTheme] = useTheme();
  const options: { value: ThemeChoice; label: string; hint: string }[] = [
    { value: "light", label: "Light", hint: "Force light appearance" },
    { value: "dark",  label: "Dark",  hint: "Force dark appearance" },
    { value: "auto",  label: "Auto",  hint: "Follow system (prefers-color-scheme)" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)", maxWidth: 800 }}>
      <header>
        <h1 className="hig-large-title" style={{ margin: 0 }}>Settings</h1>
        <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-2)" }}>
          Operator only. Most settings land progressively across milestones.
        </p>
      </header>

      <Card title="Appearance">
        <p className="hig-callout" style={{ color: "var(--colour-label-secondary)", marginTop: 0, marginBottom: "var(--space-4)" }}>
          Choose light, dark, or auto-follow-system.
        </p>
        <div
          role="radiogroup"
          aria-label="Theme"
          style={{
            display: "inline-flex",
            gap: 2,
            background: "var(--colour-fill-tertiary)",
            padding: 2,
            borderRadius: "var(--radius-sm)",
          }}
        >
          {options.map((o) => {
            const active = theme === o.value;
            return (
              <button
                key={o.value}
                role="radio"
                aria-checked={active}
                onClick={() => setTheme(o.value)}
                className="hig-callout"
                style={{
                  padding: "var(--space-2) var(--space-4)",
                  borderRadius: 4,
                  border: "none",
                  background: active ? "var(--colour-bg-system)" : "transparent",
                  color: "var(--colour-label)",
                  fontWeight: active ? 600 : 400,
                  cursor: "pointer",
                  boxShadow: active ? "var(--shadow-1)" : "none",
                  minHeight: 36,
                }}
              >
                {o.label}
              </button>
            );
          })}
        </div>
        <p className="hig-footnote" style={{ marginTop: "var(--space-3)" }}>
          {options.find((o) => o.value === theme)?.hint}
        </p>
      </Card>

      <Card title="Resolved ports">
        <dl style={{ display: "grid", gridTemplateColumns: "120px 1fr", rowGap: "var(--space-2)", margin: 0 }}>
          <dt className="hig-callout" style={{ color: "var(--colour-label-secondary)" }}>DB</dt>
          <dd className="hig-callout hig-numeric" style={{ margin: 0 }}>{boot?.ports.db ?? "·"}</dd>
          <dt className="hig-callout" style={{ color: "var(--colour-label-secondary)" }}>API</dt>
          <dd className="hig-callout hig-numeric" style={{ margin: 0 }}>{boot?.ports.api ?? "·"}</dd>
          <dt className="hig-callout" style={{ color: "var(--colour-label-secondary)" }}>Web</dt>
          <dd className="hig-callout hig-numeric" style={{ margin: 0 }}>{boot?.ports.web ?? "·"}</dd>
          <dt className="hig-callout" style={{ color: "var(--colour-label-secondary)" }}>Mailpit</dt>
          <dd className="hig-callout hig-numeric" style={{ margin: 0 }}>{boot?.ports.mail ?? "·"}</dd>
        </dl>
      </Card>

      <Card title="Archetype taxonomy">
        <p className="hig-body" style={{ marginTop: 0 }}>
          Currently active: <strong>{boot?.archetype_taxonomy_active?.name ?? "·"}</strong>.
        </p>
        <p className="hig-footnote">
          Spec §15 BLOCKING. Schema supports both; flip endpoint lands in M3.
        </p>
      </Card>

      <Card title="Integrations">
        <p className="hig-footnote" style={{ margin: 0 }}>
          Claude API key, Stripe keys, email provider wired in M4 and M8.
        </p>
      </Card>
    </div>
  );
}
