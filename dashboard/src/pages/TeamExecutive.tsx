/**
 * Executive Dashboard - spec §7B. Mirrors Steve's mockup slide 1:1.
 *
 * Layout (top to bottom):
 *  1. Page title strip
 *  2. Top KPI strip (4 equal-width cards)
 *  3. SCORE DISTRIBUTION BY BAND (one stacked bar per trait)
 *  4. Team Trait Averages (4 cards)
 *  5. ARCHETYPE BREAKDOWN (horizontal bars)
 *  6. PRIORITY COACHING INTERVENTIONS (4 cards)
 *  7. Download Executive Summary (PDF) - top-right action
 *  8. Footer: decipher.com.au · Confidential · {Role} Use Only · {Month YYYY}
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

  if (!overview) {
    return <p style={{ color: "var(--colour-text-tertiary)" }}>Loading executive view...</p>;
  }

  const role = overview.team.role_label ?? "Executive";
  const nReps = overview.n_respondents;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      {/* 1. Page title strip + export action */}
      <header style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "var(--space-4)" }}>
        <div>
          <h1 style={{ fontSize: "var(--type-title-1)", fontWeight: 600, margin: 0, letterSpacing: "-0.02em" }}>
            {overview.team.name} · Decipher DNA Audit
          </h1>
          <p style={{ margin: "var(--space-1) 0 0 0", color: "var(--colour-text-secondary)" }}>
            {role} Dashboard, {nReps} Respondents · {overview.month_label}
          </p>
        </div>
        <Button href={`/api/teams/${id}/export.pdf`} download variant="filled">
          Download Executive Summary (PDF) ↓
        </Button>
      </header>

      {/* 2. Top KPI strip */}
      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "var(--space-4)",
        }}
      >
        <KpiCard
          label="TEAM AVERAGE SCORE"
          value={overview.team_average_score_100 ?? "-"}
          suffix="/100"
          hint="across all 4 traits"
        />
        <KpiCard
          label="ELITE PERFORMERS"
          value={overview.elite_performers}
          hint="85+ across all 4 traits"
          tone="elite"
        />
        <KpiCard
          label="AT-RISK REPS"
          value={overview.at_risk_reps}
          hint="Developing in 2+ traits"
          tone="risk"
        />
        <KpiCard
          label="BIGGEST GAP TRAIT"
          value={overview.biggest_gap?.trait ?? "-"}
          hint={
            overview.biggest_gap
              ? `${overview.biggest_gap.score_100} /100 · ${overview.biggest_gap.band}`
              : ""
          }
          big={false}
        />
      </section>

      {/* 3. Distribution by band */}
      <Card>
        <SectionEyebrow>Score Distribution by Band</SectionEyebrow>
        <p style={{ color: "var(--colour-text-secondary)", marginTop: "var(--space-1)", marginBottom: "var(--space-4)" }}>
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

      {/* 4. Team trait averages */}
      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "var(--space-4)",
        }}
      >
        {traits?.map((t) => (
          <Card key={t.trait}>
            <SectionEyebrow>{t.trait}</SectionEyebrow>
            <div style={{ fontSize: "var(--type-large-title)", fontWeight: 700, fontFamily: "ui-monospace", marginTop: "var(--space-2)" }}>
              {t.score_100.toFixed(1)}
            </div>
            <div style={{ marginTop: "var(--space-2)" }}>
              <BandPill band={t.band} />
            </div>
          </Card>
        ))}
      </section>

      {/* 5. Archetype breakdown */}
      <Card>
        <SectionEyebrow>Archetype Breakdown</SectionEyebrow>
        <div style={{ marginTop: "var(--space-4)", display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
          {archetypes?.map((a) => {
            const max = Math.max(...(archetypes?.map((x) => x.n) ?? [1]));
            const pct = (a.n / max) * 100;
            return (
              <div key={a.code} style={{ display: "grid", gridTemplateColumns: "180px 1fr 40px", gap: "var(--space-3)", alignItems: "center" }}>
                <div style={{ fontSize: "var(--type-callout)" }}>{a.name}</div>
                <div style={{ height: 18, background: "var(--colour-fill-secondary)", borderRadius: "var(--radius-sm)", overflow: "hidden" }}>
                  <div style={{ width: `${pct}%`, height: "100%", background: "var(--colour-fill-primary)" }} />
                </div>
                <div style={{ fontFamily: "ui-monospace", textAlign: "right" }}>{a.n}</div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* 6. Priority coaching interventions */}
      <Card>
        <SectionEyebrow>Priority Coaching Interventions</SectionEyebrow>
        <div
          style={{
            marginTop: "var(--space-4)",
            display: "grid",
            gridTemplateColumns: "repeat(2, 1fr)",
            gap: "var(--space-4)",
          }}
        >
          {interventions?.map((i, idx) => (
            <div
              key={idx}
              style={{
                background: "var(--colour-bg-base)",
                border: "1px solid var(--colour-border-subtle)",
                borderRadius: "var(--radius-sm)",
                padding: "var(--space-4)",
                borderLeft: i.kind === "leverage"
                  ? "3px solid var(--colour-band-elite)"
                  : "3px solid var(--colour-band-developing)",
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: "var(--space-2)" }}>{i.headline}</div>
              <div style={{ color: "var(--colour-text-secondary)", fontSize: "var(--type-callout)" }}>
                {i.body}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* 7. Footer */}
      <footer
        style={{
          textAlign: "center",
          color: "var(--colour-text-tertiary)",
          fontSize: "var(--type-footnote)",
          padding: "var(--space-5) 0",
          borderTop: "1px solid var(--colour-border-subtle)",
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
    tone === "elite" ? "var(--colour-band-elite)"
    : tone === "risk" ? "var(--colour-band-developing)"
    : "var(--colour-text-primary)";
  return (
    <Card>
      <SectionEyebrow>{label}</SectionEyebrow>
      <div
        style={{
          fontSize: big ? "var(--type-large-title)" : "var(--type-title-2)",
          fontWeight: 700,
          fontFamily: big ? "ui-monospace" : undefined,
          marginTop: "var(--space-2)",
          color: colour,
          lineHeight: 1.1,
        }}
      >
        {value}
        {suffix && <span style={{ fontSize: "var(--type-title-3)", color: "var(--colour-text-tertiary)" }}>{suffix}</span>}
      </div>
      {hint && (
        <div style={{ color: "var(--colour-text-tertiary)", fontSize: "var(--type-footnote)", marginTop: "var(--space-2)" }}>
          {hint}
        </div>
      )}
    </Card>
  );
}

function BandPill({ band }: { band: string }) {
  const colour = {
    Elite: "var(--colour-band-elite)",
    Performing: "var(--colour-band-performing)",
    Practising: "var(--colour-band-practising)",
    Developing: "var(--colour-band-developing)",
  }[band] ?? "var(--colour-text-tertiary)";
  return (
    <span
      style={{
        background: colour,
        color: "#fff",
        fontSize: "var(--type-caption)",
        padding: "2px 8px",
        borderRadius: 999,
        fontWeight: 600,
        letterSpacing: "0.02em",
      }}
    >
      {band}
    </span>
  );
}
