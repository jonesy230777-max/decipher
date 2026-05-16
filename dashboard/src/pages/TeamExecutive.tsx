/**
 * Executive Dashboard — spec §7B. Mirrors Steve's mockup slide 1:1.
 * HIG-conformant: SF Pro typography, tabular numerals, semantic colours,
 * 14-pt corner radius cards, 8-pt grid spacing, accent-tinted primary button.
 */
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import { Card, SectionEyebrow, Button } from "../components/Card";
import { BandBar } from "../components/BandBar";

type Overview = {
  team: { team_id: number; name: string; role_label: string | null; organisation: string | null };
  month_label: string;
  n_respondents: number;
  team_average_score_100: number | null;
  elite_performers: number;
  at_risk_reps: number;
  biggest_gap: { trait: string; score_100: number; band: string } | null;
};
type Distribution = {
  distribution: {
    dimension: string;
    dimension_label: string;
    elite: number;
    performing: number;
    practising: number;
    developing: number;
    total: number;
  }[];
};
type TraitAvg = { trait: string; score_100: number; band: string };
type Archetype = { code: string; name: string; n: number };
type Intervention = { headline: string; body: string; kind: "at_risk" | "leverage" };

export default function TeamExecutive() {
  const { teamId } = useParams();
  const id = Number(teamId ?? 1);

  const [overview, setOverview] = useState<Overview | null>(null);
  const [dist, setDist] = useState<Distribution | null>(null);
  const [traits, setTraits] = useState<TraitAvg[] | null>(null);
  const [archetypes, setArchetypes] = useState<Archetype[] | null>(null);
  const [interventions, setInterventions] = useState<Intervention[] | null>(null);

  useEffect(() => {
    api<Overview>(`/api/teams/${id}/overview`).then(setOverview);
    api<Distribution>(`/api/teams/${id}/distribution`).then(setDist);
    api<{ trait_averages: TraitAvg[] }>(`/api/teams/${id}/trait-averages`).then((d) => setTraits(d.trait_averages));
    api<{ archetypes: Archetype[] }>(`/api/teams/${id}/archetypes`).then((d) => setArchetypes(d.archetypes));
    api<{ interventions: Intervention[] }>(`/api/teams/${id}/interventions`).then((d) => setInterventions(d.interventions));
  }, [id]);

  if (!overview) return <p className="hig-footnote">Loading executive view...</p>;

  const role = overview.team.role_label ?? "Executive";
  const nReps = overview.n_respondents;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)", maxWidth: 1400 }}>
      {/* Title + export */}
      <header style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "var(--space-5)" }}>
        <div>
          <h1 className="hig-large-title" style={{ margin: 0 }}>
            {overview.team.name} · Decipher DNA Audit
          </h1>
          <p className="hig-subhead" style={{ margin: "var(--space-1) 0 0 0" }}>
            {role} Dashboard, {nReps} Respondents · {overview.month_label}
          </p>
        </div>
        <Button href={`/api/teams/${id}/export.pdf`} download variant="filled" size="lg">
          Download Executive Summary (PDF) ↓
        </Button>
      </header>

      {/* KPI strip — 4 equal */}
      <section style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "var(--space-4)" }}>
        <KpiCard
          label="Team average score"
          value={overview.team_average_score_100 ?? "-"}
          suffix="/100"
          hint="across all 4 traits"
        />
        <KpiCard
          label="Elite performers"
          value={overview.elite_performers}
          hint="85+ across all 4 traits"
          tone="elite"
        />
        <KpiCard
          label="At-risk reps"
          value={overview.at_risk_reps}
          hint="Developing in 2+ traits"
          tone="risk"
        />
        <KpiCard
          label="Biggest gap trait"
          value={overview.biggest_gap?.trait ?? "-"}
          hint={
            overview.biggest_gap
              ? `${overview.biggest_gap.score_100} /100 · ${overview.biggest_gap.band}`
              : ""
          }
          big={false}
        />
      </section>

      {/* Distribution by band */}
      <Card>
        <SectionEyebrow>Score distribution by band</SectionEyebrow>
        <h2 className="hig-title-3" style={{ margin: "var(--space-1) 0 var(--space-3) 0" }}>
          How the {nReps} reps split per trait
        </h2>
        <p className="hig-callout" style={{ color: "var(--colour-label-secondary)", marginTop: 0, marginBottom: "var(--space-4)" }}>
          Each bar shows how the {nReps} reps are distributed across the 4 performance bands per trait.
        </p>
        {dist?.distribution.map((d) => (
          <BandBar
            key={d.dimension}
            label={d.dimension_label}
            elite={d.elite}
            performing={d.performing}
            practising={d.practising}
            developing={d.developing}
          />
        ))}
      </Card>

      {/* Team trait averages */}
      <section style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "var(--space-4)" }}>
        {traits?.map((t) => (
          <Card key={t.trait}>
            <SectionEyebrow>{t.trait}</SectionEyebrow>
            <div className="hig-large-title" style={{ marginTop: "var(--space-1)" }}>
              {t.score_100.toFixed(1)}
            </div>
            <div style={{ marginTop: "var(--space-2)" }}>
              <BandPill band={t.band} />
            </div>
          </Card>
        ))}
      </section>

      {/* Archetype breakdown */}
      <Card title="Archetype breakdown">
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
          {archetypes?.map((a) => {
            const max = Math.max(...(archetypes?.map((x) => x.n) ?? [1]));
            const pct = (a.n / max) * 100;
            return (
              <div key={a.code} style={{ display: "grid", gridTemplateColumns: "200px 1fr 48px", gap: "var(--space-3)", alignItems: "center" }}>
                <div className="hig-body">{a.name}</div>
                <div style={{ height: 16, background: "var(--colour-fill-quaternary)", borderRadius: "var(--radius-sm)", overflow: "hidden" }}>
                  <div style={{ width: `${pct}%`, height: "100%", background: "var(--colour-accent)" }} />
                </div>
                <div className="hig-numeric hig-body" style={{ textAlign: "right", color: "var(--colour-label-secondary)" }}>
                  {a.n}
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Priority coaching interventions */}
      <Card title="Priority coaching interventions">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "var(--space-4)" }}>
          {interventions?.map((i, idx) => (
            <div
              key={idx}
              style={{
                background: "var(--colour-bg-system)",
                border: "1px solid var(--colour-separator-opaque)",
                borderRadius: "var(--radius-md)",
                padding: "var(--space-4)",
                borderLeft: i.kind === "leverage"
                  ? "3px solid var(--colour-system-green)"
                  : "3px solid var(--colour-system-red)",
              }}
            >
              <div className="hig-headline" style={{ marginBottom: "var(--space-2)" }}>{i.headline}</div>
              <div className="hig-callout" style={{ color: "var(--colour-label-secondary)" }}>{i.body}</div>
            </div>
          ))}
        </div>
      </Card>

      <footer
        className="hig-footnote"
        style={{
          textAlign: "center",
          padding: "var(--space-5) 0",
          borderTop: "1px solid var(--colour-separator-opaque)",
        }}
      >
        decipher.com.au · Confidential, For {role} Use Only · {overview.month_label}
      </footer>
    </div>
  );
}

function KpiCard({
  label, value, suffix, hint, tone, big = true,
}: {
  label: string;
  value: string | number;
  suffix?: string;
  hint?: string;
  tone?: "elite" | "risk";
  big?: boolean;
}) {
  const colour =
    tone === "elite" ? "var(--colour-system-green)"
    : tone === "risk" ? "var(--colour-system-red)"
    : "var(--colour-label)";
  return (
    <Card>
      <SectionEyebrow>{label}</SectionEyebrow>
      <div
        className={big ? "hig-large-title" : "hig-title-2"}
        style={{ color: colour, marginTop: "var(--space-1)" }}
      >
        {value}
        {suffix && (
          <span className="hig-title-3" style={{ color: "var(--colour-label-tertiary)", marginLeft: 2 }}>
            {suffix}
          </span>
        )}
      </div>
      {hint && (
        <div className="hig-caption-1" style={{ marginTop: "var(--space-2)" }}>{hint}</div>
      )}
    </Card>
  );
}

function BandPill({ band }: { band: string }) {
  const colour = {
    Elite:      "var(--colour-band-elite)",
    Performing: "var(--colour-band-performing)",
    Practising: "var(--colour-band-practising)",
    Developing: "var(--colour-band-developing)",
  }[band] ?? "var(--colour-label-tertiary)";
  return (
    <span
      style={{
        background: colour,
        color: "#FFFFFF",
        fontSize: "var(--type-caption-1)",
        lineHeight: "var(--lead-caption-1)",
        padding: "2px 10px",
        borderRadius: "var(--radius-pill)",
        fontWeight: 600,
      }}
    >
      {band}
    </span>
  );
}
