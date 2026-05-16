import type { Bootstrap } from "../api";

export default function Settings({ boot }: { boot: Bootstrap | null }) {
  return (
    <div style={{ maxWidth: 720 }}>
      <h1 style={{ fontSize: "var(--type-title-1)", fontWeight: 600, margin: 0 }}>Settings</h1>
      <p style={{ color: "var(--colour-text-secondary)", marginTop: "var(--space-3)" }}>
        Operator-only. Most settings land progressively across milestones.
      </p>

      <section style={{ marginTop: "var(--space-6)" }}>
        <h2 style={{ fontSize: "var(--type-title-3)", fontWeight: 600, margin: 0 }}>Resolved ports</h2>
        <dl style={{ marginTop: "var(--space-3)", display: "grid", gridTemplateColumns: "120px 1fr", rowGap: "var(--space-2)" }}>
          <dt style={{ color: "var(--colour-text-secondary)" }}>DB</dt>
          <dd style={{ margin: 0, fontFamily: "ui-monospace" }}>{boot?.ports.db ?? "—"}</dd>
          <dt style={{ color: "var(--colour-text-secondary)" }}>API</dt>
          <dd style={{ margin: 0, fontFamily: "ui-monospace" }}>{boot?.ports.api ?? "—"}</dd>
          <dt style={{ color: "var(--colour-text-secondary)" }}>Web</dt>
          <dd style={{ margin: 0, fontFamily: "ui-monospace" }}>{boot?.ports.web ?? "—"}</dd>
          <dt style={{ color: "var(--colour-text-secondary)" }}>Mailpit</dt>
          <dd style={{ margin: 0, fontFamily: "ui-monospace" }}>{boot?.ports.mail ?? "—"}</dd>
        </dl>
      </section>

      <section style={{ marginTop: "var(--space-6)" }}>
        <h2 style={{ fontSize: "var(--type-title-3)", fontWeight: 600, margin: 0 }}>Archetype taxonomy</h2>
        <p style={{ color: "var(--colour-text-secondary)", marginTop: "var(--space-2)" }}>
          Currently active: <strong>{boot?.archetype_taxonomy_active?.name ?? "—"}</strong>.
        </p>
        <p style={{ color: "var(--colour-text-tertiary)", marginTop: "var(--space-2)", fontSize: "var(--type-footnote)" }}>
          Spec §15 BLOCKING. Schema supports both; flip endpoint lands in M3.
        </p>
      </section>

      <section style={{ marginTop: "var(--space-6)" }}>
        <h2 style={{ fontSize: "var(--type-title-3)", fontWeight: 600, margin: 0 }}>Integrations</h2>
        <p style={{ color: "var(--colour-text-tertiary)", marginTop: "var(--space-2)", fontSize: "var(--type-footnote)" }}>
          Claude API key, Stripe keys, email provider — wired in M4 + M8.
        </p>
      </section>
    </div>
  );
}
