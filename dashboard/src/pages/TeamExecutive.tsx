/**
 * Executive Dashboard — spec §7B. Mirrors Steve's mockup slide 1:1.
 * HIG-conformant: SF Pro typography, tabular numerals, semantic colours,
 * 14-pt corner radius cards, 8-pt grid spacing, accent-tinted primary button.
 */
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, downloadFile } from "../api";
import { Card, SectionEyebrow, Button } from "../components/Card";
import { BandBar } from "../components/BandBar";
import { GapAnalysis } from "../components/GapAnalysis";

type RosterRow = {
  respondent_id: number;
  name: string;
  email: string;
  consent_share_individual: boolean;
  cognitive_empathy: number | null;
  eq: number | null;
  pressure_composure: number | null;
  storytelling: number | null;
  overall: number | null;
  archetype_name: string | null;
  latest_audit_at: string | null;
};

type Overview = {
  team: { team_id: number; name: string; role_label: string | null; organisation: string | null };
  month_label: string;
  n_respondents: number;
  team_average_score_100: number | null;
  elite_performers: number;
  at_risk_reps: number;
  biggest_gap: { trait: string; score_100: number; band: string } | null;
  director: { respondent_id: number; name: string | null; email: string; role: string } | null;
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
  const [roster, setRoster] = useState<RosterRow[] | null>(null);

  useEffect(() => {
    api<Overview>(`/api/teams/${id}/overview`).then(setOverview);
    api<Distribution>(`/api/teams/${id}/distribution`).then(setDist);
    api<{ trait_averages: TraitAvg[] }>(`/api/teams/${id}/trait-averages`).then((d) => setTraits(d.trait_averages));
    api<{ archetypes: Archetype[] }>(`/api/teams/${id}/archetypes`).then((d) => setArchetypes(d.archetypes));
    api<{ interventions: Intervention[] }>(`/api/teams/${id}/interventions`).then((d) => setInterventions(d.interventions));
    api<{ roster: RosterRow[] }>(`/api/teams/${id}/roster`).then((d) => setRoster(d.roster));
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
          {overview.director && (
            <p className="hig-footnote" style={{ margin: "var(--space-1) 0 0 0", color: "var(--colour-label-secondary)" }}>
              Director: <strong style={{ color: "var(--colour-label)" }}>{overview.director.name ?? overview.director.email}</strong>
              {" · "}{overview.director.email}
            </p>
          )}
        </div>
        <div style={{ display: "flex", gap: "var(--space-2)" }}>
          <InviteRespondentButton teamId={id} />
          <Button onClick={() => downloadFile(`/api/teams/${id}/export.pdf`, `team-${id}-executive-summary.pdf`)} variant="filled" size="lg">
            Download Executive Summary (PDF) ↓
          </Button>
        </div>
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
      <Card title="Archetype Breakdown">
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
      <Card title="Priority Coaching Interventions">
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

      {/* Gap analysis (team vs cohort) */}
      <GapAnalysis kind="team" href={`/api/teams/${id}/gap-analysis`} />

      {/* Team roster (consent-gated individual drill-down per user story) */}
      {roster && (
        <Card title={`Team roster (${roster.length})`}>
          <p className="hig-callout" style={{ color: "var(--colour-label-secondary)", margin: "0 0 var(--space-3) 0" }}>
            Rows with a green identity link have consented to share individual reports.
            Anonymised rows still show scores + archetype + band; name and email are
            withheld until consent is granted.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1.2fr 0.6fr 0.6fr 0.6fr 0.6fr 0.7fr 1fr", columnGap: "var(--space-3)", rowGap: "var(--space-2)", alignItems: "center" }}>
            <RosterHead>Name</RosterHead>
            <RosterHead>Email</RosterHead>
            <RosterHead align="right">CE</RosterHead>
            <RosterHead align="right">EQ</RosterHead>
            <RosterHead align="right">PC</RosterHead>
            <RosterHead align="right">ST</RosterHead>
            <RosterHead align="right">Overall</RosterHead>
            <RosterHead>Archetype</RosterHead>
            {roster.slice(0, 25).map((r) => {
              const consented = r.consent_share_individual;
              return (
                <RosterRowEl key={r.respondent_id} r={r} consented={consented} />
              );
            })}
          </div>
          {roster.length > 25 && (
            <div className="hig-footnote" style={{ marginTop: "var(--space-3)", color: "var(--colour-label-tertiary)" }}>
              Showing top 25 of {roster.length} by overall score.
            </div>
          )}
        </Card>
      )}

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

function InviteRespondentButton({ teamId }: { teamId: number }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg]   = useState<string | null>(null);
  async function send() {
    const email = prompt("Email address to invite:");
    if (!email) return;
    const first = prompt("First name (optional):") || null;
    const last  = prompt("Last name (optional):")  || null;
    setBusy(true);
    try {
      const json = await api<{ delivered: boolean; link?: string; error?: string }>("/api/audit/invite", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, first_name: first, last_name: last, team_id: teamId }),
      });
      setMsg(json.delivered
        ? `Invite delivered to ${email}.`
        : `Recorded but SMTP failed: ${json.error}`);
    } catch (e) {
      setMsg(`Failed: ${e instanceof Error ? e.message : "unknown error"}`);
    } finally {
      setTimeout(() => setMsg(null), 6000);
      setBusy(false);
    }
  }
  return (
    <>
      <Button variant="tinted" size="lg" onClick={send}>
        {busy ? "Sending..." : "Invite rep ✉"}
      </Button>
      {msg && (
        <div className="hig-caption-1"
             style={{ position: "fixed", bottom: 24, right: 24, zIndex: 80,
                      background: "var(--colour-bg-system-secondary)",
                      border: "1px solid var(--colour-separator-opaque)",
                      borderRadius: 8, padding: 12, boxShadow: "var(--shadow-2)",
                      maxWidth: 360 }}>
          {msg}
        </div>
      )}
    </>
  );
}

function RosterHead({ children, align }: { children: React.ReactNode; align?: "right" }) {
  return (
    <div
      className="hig-caption-1"
      style={{
        textTransform: "uppercase",
        letterSpacing: "0.04em",
        color: "var(--colour-label-tertiary)",
        padding: "var(--space-2) 0",
        borderBottom: "1px solid var(--colour-separator)",
        textAlign: align ?? "left",
      }}
    >
      {children}
    </div>
  );
}

function RosterRowEl({ r, consented }: { r: RosterRow; consented: boolean }) {
  const overall = r.overall != null ? (r.overall * 100).toFixed(0) : "-";
  const fmt = (v: number | null) => (v != null ? (v * 100).toFixed(0) : "-");
  const nameCell = consented ? (
    <Link to={`/respondents/${r.respondent_id}`} style={{ color: "var(--colour-accent)", fontWeight: 600, textDecoration: "none" }}>
      {r.name}
    </Link>
  ) : (
    <span style={{ color: "var(--colour-label-secondary)" }}>{r.name}</span>
  );
  const rowStyle = {
    padding: "var(--space-2) 0",
    borderBottom: "1px solid var(--colour-separator)",
  } as React.CSSProperties;
  return (
    <>
      <div className="hig-callout" style={rowStyle}>{nameCell}</div>
      <div className="hig-footnote" style={{ ...rowStyle, color: "var(--colour-label-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.email}</div>
      <div className="hig-callout hig-numeric" style={{ ...rowStyle, textAlign: "right" }}>{fmt(r.cognitive_empathy)}</div>
      <div className="hig-callout hig-numeric" style={{ ...rowStyle, textAlign: "right" }}>{fmt(r.eq)}</div>
      <div className="hig-callout hig-numeric" style={{ ...rowStyle, textAlign: "right" }}>{fmt(r.pressure_composure)}</div>
      <div className="hig-callout hig-numeric" style={{ ...rowStyle, textAlign: "right" }}>{fmt(r.storytelling)}</div>
      <div className="hig-callout hig-numeric" style={{ ...rowStyle, textAlign: "right", fontWeight: 600 }}>{overall}</div>
      <div className="hig-footnote" style={{ ...rowStyle, color: "var(--colour-label-secondary)" }}>{r.archetype_name ?? "-"}</div>
    </>
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
