import { Stat } from "../components/Stat";
import type { Bootstrap } from "../api";

export default function MissionControl({ boot }: { boot: Bootstrap | null }) {
  if (!boot) {
    return <p style={{ color: "var(--colour-text-tertiary)" }}>Loading...</p>;
  }
  const c = boot.counts;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      <header>
        <h1
          style={{
            fontSize: "var(--type-title-1)",
            fontWeight: 600,
            margin: 0,
            letterSpacing: "-0.02em",
          }}
        >
          Mission Control
        </h1>
        <p
          style={{
            margin: "var(--space-2) 0 0 0",
            color: "var(--colour-text-secondary)",
            fontSize: "var(--type-callout)",
            maxWidth: 640,
          }}
        >
          Diagnose before prescribe. The DNA Audit is the entry point.
          Consulting and training are the prescription.
        </p>
      </header>

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "var(--space-4)",
        }}
      >
        <Stat label="Respondents" value={c.respondents} hint="audits issued, all-time" />
        <Stat label="Audits today" value={c.audits_today} hint="started in the last 24h" />
        <Stat label="This month" value={c.audits_month} hint="started this calendar month" />
        <Stat label="Reports delivered" value={c.reports} hint="PDFs generated, all-time" />
        <Stat label="Validated patterns" value={c.patterns_doubt_passed} hint="cleared the DOUBT gate" />
        <Stat label="Industries live" value={c.industries} hint="question banks active" />
        <Stat label="Bespoke clients" value={c.bespoke_clients} hint="active engagements" />
        <Stat label="Events 24h" value={c.events_24h} hint="from events_log" />
      </section>

      <section>
        <h2 style={{ fontSize: "var(--type-title-3)", fontWeight: 600, margin: "0 0 var(--space-2) 0" }}>
          Active archetype taxonomy
        </h2>
        <p style={{ color: "var(--colour-text-secondary)", margin: 0 }}>
          {boot.archetype_taxonomy_active?.name ?? "-"} (taxonomy id{" "}
          {boot.archetype_taxonomy_active?.taxonomy_id ?? "-"}). Switch in Settings once Steve confirms.
        </p>
      </section>

      <footer style={{ color: "var(--colour-text-tertiary)", fontSize: "var(--type-footnote)" }}>
        Bootstrapped {new Date(boot.served_at).toLocaleString("en-AU")}.
      </footer>
    </div>
  );
}
