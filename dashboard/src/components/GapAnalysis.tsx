/**
 * Gap analysis block. Reusable for a team (score vs cohort) or an
 * individual (score vs team mean vs cohort mean).
 *
 *   <GapAnalysis kind="team"       href="/api/teams/1/gap-analysis" />
 *   <GapAnalysis kind="individual" href="/api/respondents/1368/gap-analysis" />
 */
import { useEffect, useState } from "react";
import { Card } from "./Card";
import { api } from "../api";

export type GapRow = {
  dimension: string;
  label: string;
  score_100: number | null;
  band: string;
  cohort_100?: number | null;            // team analysis
  delta_vs_cohort_100?: number | null;
  team_mean_100?: number | null;         // individual analysis
  cohort_mean_100?: number | null;
  delta_vs_team_100?: number | null;
  gap_to_elite_pts: number | null;
  gap_to_performing_pts: number | null;
};
type Payload = {
  n_respondents?: number;
  gaps: GapRow[];
  weakest_dimension: GapRow | null;
  strongest_dimension: GapRow | null;
  top_quartile?: { respondent_id: number; name: string; score_100: number | null }[];
  bottom_quartile?: { respondent_id: number; name: string; score_100: number | null }[];
};

const BAND_COLOUR: Record<string, string> = {
  elite:      "var(--colour-band-elite)",
  performing: "var(--colour-band-performing)",
  practising: "var(--colour-band-practising)",
  developing: "var(--colour-band-developing)",
  unknown:    "var(--colour-label-tertiary)",
};

export function GapAnalysis({ kind, href }: { kind: "team" | "individual"; href: string }) {
  const [data, setData] = useState<Payload | null>(null);
  useEffect(() => { api<Payload>(href).then(setData).catch(() => {}); }, [href]);
  if (!data) return <Card title="Gap Analysis"><p className="hig-footnote">Loading…</p></Card>;
  if (!data.gaps?.length) return <Card title="Gap Analysis"><p className="hig-footnote">No scored audits yet.</p></Card>;

  const weakest = data.weakest_dimension;
  const strongest = data.strongest_dimension;
  const cmpLabel = kind === "team" ? "Cohort" : "Team mean";
  const cmpKey: keyof GapRow = kind === "team" ? "cohort_100" : "team_mean_100";
  const deltaKey: keyof GapRow = kind === "team" ? "delta_vs_cohort_100" : "delta_vs_team_100";

  return (
    <Card title={`Gap Analysis ${kind === "team" ? "(team vs cohort)" : "(individual vs team + cohort)"}`}>
      {/* Headline */}
      {weakest && (
        <div style={{ display: "flex", gap: "var(--space-4)", marginBottom: "var(--space-3)" }}>
          <Headline label="Biggest gap"
                    value={`${weakest.label} · ${weakest.score_100} /100`}
                    sub={weakest.gap_to_performing_pts != null && weakest.gap_to_performing_pts > 0
                      ? `${weakest.gap_to_performing_pts.toFixed(1)} pts to reach Performing`
                      : `In ${weakest.band}`}
                    tone="risk" />
          {strongest && (
            <Headline label="Top trait"
                      value={`${strongest.label} · ${strongest.score_100} /100`}
                      sub={strongest.gap_to_elite_pts != null && strongest.gap_to_elite_pts > 0
                        ? `${strongest.gap_to_elite_pts.toFixed(1)} pts to reach Elite`
                        : `At Elite`}
                      tone="elite" />
          )}
        </div>
      )}

      {/* Per-dimension breakdown */}
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--type-footnote)" }}>
        <thead>
          <tr>
            {["Trait","Score /100","Band",cmpLabel,"Δ",`Gap to Performing`,"Gap to Elite"].map(h => (
              <th key={h} className="hig-caption-1"
                  style={{ textAlign: "left", textTransform: "uppercase", letterSpacing: "0.04em",
                           padding: "var(--space-2)", color: "var(--colour-label-tertiary)",
                           borderBottom: "1px solid var(--colour-separator)" }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.gaps.map((g) => {
            const cmp = g[cmpKey] as number | null | undefined;
            const delta = g[deltaKey] as number | null | undefined;
            return (
              <tr key={g.dimension} style={{ borderBottom: "1px solid var(--colour-separator)" }}>
                <td style={{ padding: "var(--space-2)", fontWeight: 600 }}>{g.label}</td>
                <td style={{ padding: "var(--space-2)", fontVariantNumeric: "tabular-nums", fontWeight: 700 }}>{g.score_100 ?? "·"}</td>
                <td style={{ padding: "var(--space-2)" }}>
                  <span style={{ background: BAND_COLOUR[g.band], color: "#FFFFFF",
                                  borderRadius: 999, padding: "2px 8px",
                                  fontSize: 10, fontWeight: 700, textTransform: "capitalize" }}>
                    {g.band}
                  </span>
                </td>
                <td style={{ padding: "var(--space-2)", fontVariantNumeric: "tabular-nums",
                             color: "var(--colour-label-secondary)" }}>{cmp ?? "·"}</td>
                <td style={{ padding: "var(--space-2)", fontVariantNumeric: "tabular-nums",
                             color: delta == null
                               ? "var(--colour-label-tertiary)"
                               : delta >= 0 ? "var(--colour-system-green)" : "var(--colour-system-red)",
                             fontWeight: 700 }}>
                  {delta == null ? "·" : `${delta >= 0 ? "+" : ""}${delta.toFixed(1)}`}
                </td>
                <td style={{ padding: "var(--space-2)", fontVariantNumeric: "tabular-nums",
                             color: g.gap_to_performing_pts != null && g.gap_to_performing_pts > 0
                               ? "var(--colour-system-orange)" : "var(--colour-label-tertiary)" }}>
                  {g.gap_to_performing_pts != null && g.gap_to_performing_pts > 0
                    ? `${g.gap_to_performing_pts.toFixed(1)} pts` : "-"}
                </td>
                <td style={{ padding: "var(--space-2)", fontVariantNumeric: "tabular-nums",
                             color: g.gap_to_elite_pts != null && g.gap_to_elite_pts > 0
                               ? "var(--colour-label-secondary)" : "var(--colour-label-tertiary)" }}>
                  {g.gap_to_elite_pts != null && g.gap_to_elite_pts > 0
                    ? `${g.gap_to_elite_pts.toFixed(1)} pts` : "-"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Team quartiles */}
      {kind === "team" && data.top_quartile && data.bottom_quartile && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)",
                      marginTop: "var(--space-4)" }}>
          <Quartile title="Top quartile (model the behaviour)"
                    rows={data.top_quartile} tone="elite" />
          <Quartile title="Bottom quartile (coaching priority)"
                    rows={data.bottom_quartile} tone="risk" />
        </div>
      )}
    </Card>
  );
}

function Headline({ label, value, sub, tone }: { label: string; value: string; sub: string; tone: "risk" | "elite" }) {
  const colour = tone === "elite" ? "var(--colour-system-green)" : "var(--colour-system-orange)";
  return (
    <div style={{ flex: 1, padding: "var(--space-3)",
                  background: "var(--colour-bg-system)",
                  border: `1px solid ${colour}`,
                  borderRadius: "var(--radius-md)" }}>
      <div className="hig-caption-1" style={{ color: colour, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em" }}>{label}</div>
      <div className="hig-title-3" style={{ marginTop: 2 }}>{value}</div>
      <div className="hig-caption-1" style={{ color: "var(--colour-label-secondary)", marginTop: 2 }}>{sub}</div>
    </div>
  );
}
function Quartile({ title, rows, tone }: {
  title: string;
  rows: { respondent_id: number; name: string; score_100: number | null }[];
  tone: "elite" | "risk";
}) {
  const colour = tone === "elite" ? "var(--colour-system-green)" : "var(--colour-system-red)";
  return (
    <div>
      <div className="hig-caption-1" style={{ color: colour, fontWeight: 700,
              textTransform: "uppercase", letterSpacing: "0.04em",
              marginBottom: "var(--space-2)" }}>
        {title}
      </div>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {rows.map((r) => (
          <li key={r.respondent_id} style={{
            display: "flex", justifyContent: "space-between",
            padding: "6px 0", borderTop: "1px solid var(--colour-separator)",
          }}>
            <a href={`/respondents/${r.respondent_id}`} style={{ color: "var(--colour-accent)",
                                                                  textDecoration: "none", fontWeight: 600 }}>
              {r.name}
            </a>
            <span className="hig-numeric">{r.score_100 ?? "·"}</span>
          </li>
        ))}
        {rows.length === 0 && <li className="hig-footnote">(not enough data)</li>}
      </ul>
    </div>
  );
}
