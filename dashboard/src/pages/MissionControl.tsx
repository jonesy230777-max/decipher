import { Stat } from "../components/Stat";
import { Card } from "../components/Card";
import type { Bootstrap } from "../api";

export default function MissionControl({ boot }: { boot: Bootstrap | null }) {
  if (!boot) {
    return <p className="hig-footnote">Loading...</p>;
  }
  const c = boot.counts;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)", maxWidth: 1280 }}>
      <header>
        <h1 className="hig-large-title" style={{ margin: 0 }}>Mission Control</h1>
        <p className="hig-body" style={{ margin: "var(--space-2) 0 0 0", color: "var(--colour-label-secondary)", maxWidth: 640 }}>
          Diagnose before prescribe. The DNA Audit is the entry point. Consulting and training are the prescription.
        </p>
      </header>

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "var(--space-4)",
        }}
      >
        <Stat label="Respondents"        value={c.respondents}        hint="audits issued, all-time" />
        <Stat label="Audits today"       value={c.audits_today}       hint="started in the last 24h" />
        <Stat label="This month"         value={c.audits_month}       hint="started this calendar month" />
        <Stat label="Reports delivered"  value={c.reports}            hint="PDFs generated, all-time" />
        <Stat label="Validated patterns" value={c.patterns_doubt_passed} hint="cleared the DOUBT gate" />
        <Stat label="Industries live"    value={c.industries}         hint="question banks active" />
        <Stat label="Bespoke clients"    value={c.bespoke_clients}    hint="active engagements" />
        <Stat label="Events 24h"         value={c.events_24h}         hint="from events_log" />
      </section>

      <Card title="Active archetype taxonomy">
        <p className="hig-body" style={{ margin: 0 }}>
          {boot.archetype_taxonomy_active?.name ?? "-"} (taxonomy id{" "}
          {boot.archetype_taxonomy_active?.taxonomy_id ?? "-"}). Switch in Settings once Steve confirms.
        </p>
      </Card>

      <footer className="hig-footnote">
        Bootstrapped {new Date(boot.served_at).toLocaleString("en-AU")}.
      </footer>
    </div>
  );
}
