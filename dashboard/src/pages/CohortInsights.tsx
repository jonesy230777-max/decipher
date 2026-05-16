import { useEffect, useState } from "react";
import { api } from "../api";
import { Card, SectionEyebrow } from "../components/Card";
import { BandBar } from "../components/BandBar";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";

type Stats = {
  totals: {
    total_audits: number;
    mean_cognitive_empathy: number;
    mean_eq: number;
    mean_pressure_composure: number;
    mean_storytelling: number;
  } | null;
  by_band: { dimension: string; band: string; n: number }[];
  by_archetype: { code: string; name: string; n: number }[];
  trend: {
    snapshot_date: string;
    total_audits: number;
    mean_cognitive_empathy: number | null;
    mean_eq: number | null;
    mean_pressure_composure: number | null;
    mean_storytelling: number | null;
  }[];
};
type Pattern = {
  pattern_id: number;
  name: string;
  hit_rate: number | null;
  n_observations: number | null;
  bh_p_value: number | null;
  doubt_passed: boolean;
};

const DIM_LABEL: Record<string, string> = {
  cognitive_empathy: "Cognitive Empathy",
  eq: "EQ",
  pressure_composure: "Pressure Composure",
  storytelling: "Storytelling",
};

export default function CohortInsights() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [patterns, setPatterns] = useState<Pattern[] | null>(null);
  useEffect(() => {
    api<Stats>("/api/cohort/stats").then(setStats);
    api<{ patterns: Pattern[] }>("/api/cohort/patterns").then((d) => setPatterns(d.patterns));
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)", maxWidth: 1400 }}>
      <header>
        <h1 className="hig-large-title" style={{ margin: 0 }}>Cohort Insights</h1>
        <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-2)" }}>
          Global aggregate across every audit, every client. The Trojan-horse view.
        </p>
      </header>

      {stats?.totals && (
        <Card title="Cohort means">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "var(--space-4)" }}>
            {[
              ["Cognitive Empathy", stats.totals.mean_cognitive_empathy],
              ["EQ", stats.totals.mean_eq],
              ["Pressure Composure", stats.totals.mean_pressure_composure],
              ["Storytelling", stats.totals.mean_storytelling],
            ].map(([label, v]) => (
              <div key={label as string}>
                <SectionEyebrow>{label as string}</SectionEyebrow>
                <div className="hig-title-1 hig-numeric">{(((v as number) ?? 0) * 100).toFixed(1)}</div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card title="Distribution by band, every dimension">
        {(["cognitive_empathy", "eq", "pressure_composure", "storytelling"] as const).map((dim) => {
          const bands = stats?.by_band.filter((b) => b.dimension === dim) ?? [];
          const get = (b: string) => bands.find((x) => x.band === b)?.n ?? 0;
          return (
            <BandBar
              key={dim}
              label={DIM_LABEL[dim]}
              elite={get("elite")}
              performing={get("performing")}
              practising={get("practising")}
              developing={get("developing")}
            />
          );
        })}
      </Card>

      <Card title="Trailing 14-day means">
        {stats && stats.trend.length > 0 && (
          <div style={{ width: "100%", height: 280 }}>
            <ResponsiveContainer>
              <LineChart data={stats.trend.map((t) => ({
                date: new Date(t.snapshot_date).toLocaleDateString("en-AU", { day: "2-digit", month: "short" }),
                CE: t.mean_cognitive_empathy ? +(t.mean_cognitive_empathy * 100).toFixed(1) : null,
                EQ: t.mean_eq ? +(t.mean_eq * 100).toFixed(1) : null,
                PC: t.mean_pressure_composure ? +(t.mean_pressure_composure * 100).toFixed(1) : null,
                ST: t.mean_storytelling ? +(t.mean_storytelling * 100).toFixed(1) : null,
              }))}>
                <CartesianGrid stroke="var(--colour-separator)" strokeDasharray="3 3" />
                <XAxis dataKey="date" stroke="var(--colour-label-tertiary)" fontSize={12} />
                <YAxis domain={[40, 80]} stroke="var(--colour-label-tertiary)" fontSize={12} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="CE" stroke="var(--colour-band-elite)" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="EQ" stroke="var(--colour-band-performing)" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="PC" stroke="var(--colour-band-practising)" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="ST" stroke="var(--colour-band-developing)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      <Card
        title="Validated patterns"
        action={<span className="hig-footnote">✓ = cleared the DOUBT gate (BH p&lt;0.01, hit≥60%, OOS≥50%, robust)</span>}
      >
        {patterns && patterns.length === 0 && (
          <p className="hig-footnote">None yet. Pattern hunter runs weekly.</p>
        )}
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {patterns?.map((p) => (
            <li
              key={p.pattern_id}
              style={{
                padding: "var(--space-3) 0",
                borderTop: "1px solid var(--colour-separator)",
                display: "flex",
                alignItems: "baseline",
                gap: "var(--space-3)",
              }}
            >
              <span
                style={{
                  color: p.doubt_passed ? "var(--colour-system-green)" : "var(--colour-label-tertiary)",
                  width: 16,
                  fontWeight: 700,
                }}
                aria-label={p.doubt_passed ? "Cleared DOUBT gate" : "Candidate"}
              >
                {p.doubt_passed ? "✓" : "·"}
              </span>
              <span className="hig-callout" style={{ flex: 1 }}>{p.name}</span>
              <span className="hig-footnote hig-numeric">
                hit {p.hit_rate ? (p.hit_rate * 100).toFixed(0) : "·"}% · n={p.n_observations ?? "·"} · p={p.bh_p_value?.toFixed(4) ?? "·"}
              </span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
