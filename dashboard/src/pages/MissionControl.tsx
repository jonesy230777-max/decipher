import { useEffect, useState } from "react";
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line, ResponsiveContainer,
  XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";
import { Stat } from "../components/Stat";
import { Card } from "../components/Card";
import { TimeRange, rangeDays, type TimeRangeKey } from "../components/TimeRange";
import type { Bootstrap, DimMeans } from "../api";
import { api } from "../api";

type Series = { day: string; n_audits: number; n_reports: number; mean_overall: number };
type Funnel = { stages: { key: string; label: string; n: number }[] };
type RegionRow = { region: string; teams: number; reps: number; avg_overall: number };
type TopArch = { name: string; n: number };

const DIM_META: { key: keyof Omit<DimMeans, "n_scored">; label: string }[] = [
  { key: "cognitive_empathy",  label: "Cognitive Empathy" },
  { key: "eq",                 label: "Emotional Intelligence" },
  { key: "pressure_composure", label: "Pressure Composure" },
  { key: "storytelling",       label: "Narrative Persuasion" },
];

function dimBand(score: number): { label: string; colour: string } {
  if (score >= 85) return { label: "Elite",       colour: "#34C759" };
  if (score >= 65) return { label: "Performing",  colour: "#007AFF" };
  if (score >= 40) return { label: "Practising",  colour: "#FF9500" };
  return                   { label: "Developing", colour: "#FF3B30" };
}

const _EMPTY_DIM: DimMeans = {
  cognitive_empathy: 0, eq: 0, pressure_composure: 0, storytelling: 0, n_scored: 0,
};

function DimHealthCard({ dims, nScored, rangeLabel }: { dims: DimMeans; nScored: number; rangeLabel: string }) {
  return (
    <Card title={`Dimension health - ${rangeLabel}`}>
      <p className="hig-caption-1"
         style={{ color: "var(--colour-label-secondary)", margin: "0 0 var(--space-3)" }}>
        {nScored > 0 ? `Mean score across ${nScored} scored audit${nScored === 1 ? "" : "s"}` : "No scored audits in this window"}
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
        {DIM_META.map(({ key, label }) => {
          const score = dims[key] ?? 0;
          const { label: bandLabel, colour } = dimBand(score);
          return (
            <div key={key}>
              <div style={{ display: "flex", justifyContent: "space-between",
                            alignItems: "baseline", marginBottom: 5 }}>
                <span className="hig-callout" style={{ fontWeight: 600 }}>{label}</span>
                <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span className="hig-numeric" style={{ fontSize: 15, fontWeight: 700,
                                                          color: "var(--colour-label)" }}>
                    {score > 0 ? score.toFixed(1) : "·"}
                  </span>
                  <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 8px",
                                 borderRadius: 100, background: colour, color: "#fff",
                                 letterSpacing: "0.01em" }}>
                    {bandLabel}
                  </span>
                </span>
              </div>
              <div style={{ height: 8, borderRadius: 4,
                            background: "var(--colour-separator-opaque)" }}>
                <div style={{ height: "100%", borderRadius: 4, background: colour,
                              width: `${Math.min(score, 100)}%`,
                              transition: "width 0.4s ease" }} />
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

export default function MissionControl({ boot }: { boot: Bootstrap | null }) {
  const [series, setSeries] = useState<Series[]>([]);
  const [funnel, setFunnel] = useState<Funnel | null>(null);
  const [regions, setRegions] = useState<RegionRow[]>([]);
  const [tops, setTops] = useState<TopArch[]>([]);
  const [dims, setDims] = useState<DimMeans>(_EMPTY_DIM);
  const [range, setRange] = useState<TimeRangeKey>("30");
  const days = rangeDays(range);
  const rangeLabel = ({
    "7":   "last 7 days",
    "30":  "last 30 days",
    "180": "last 6 months",
    "365": "last 12 months",
    "all": "all time",
  } as const)[range];

  // Seed dimension means from bootstrap (30d) on first render.
  useEffect(() => {
    if (boot?.dim_means_30d) setDims(boot.dim_means_30d);
  }, [boot]);

  useEffect(() => {
    api<{ series: Series[] }>(`/api/mission/series?days=${days}`).then((d) => setSeries(d.series));
    api<Funnel>(`/api/funnel?days=${days}`).then(setFunnel);
    api<{ regions: RegionRow[] }>("/api/mission/by-region").then((d) => setRegions(d.regions));
    api<{ archetypes: TopArch[] }>("/api/mission/top-archetypes").then((d) => setTops(d.archetypes));
    api<DimMeans>(`/api/mission/dim-means?days=${days}`).then(setDims);
  }, [days]);

  if (!boot) return <p className="hig-footnote">Loading...</p>;
  const c = boot.counts;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)", maxWidth: 1400 }}>
      <header>
        <p className="hig-caption-1" style={{
          display: "inline-block", margin: 0,
          textTransform: "uppercase", letterSpacing: "0.08em",
          background: "var(--colour-accent-tint-bg)", color: "var(--colour-accent)",
          padding: "4px 10px", borderRadius: "var(--radius-pill)", fontWeight: 700,
        }}>
          Decipher · Sales DNA · State of the nation
        </p>
        <h1 className="hig-large-title" style={{ margin: "var(--space-2) 0 0 0" }}>Mission Control</h1>
        <p className="hig-body" style={{ margin: "var(--space-2) 0 0 0", color: "var(--colour-label-secondary)", maxWidth: 720 }}>
          State of the nation across every team, company, audit and report. Diagnose before prescribe.
        </p>
      </header>

      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
        <span className="hig-caption-1" style={{ color: "var(--colour-label-secondary)" }}>Window:</span>
        <TimeRange value={range} onChange={setRange} />
      </div>

      {/* KPI row */}
      <section style={{
        display: "grid",
        gridTemplateColumns: "repeat(8, 1fr)",
        gap: "var(--space-2)",
      }}>
        <Stat label="Respondents"        value={c.respondents}        hint="all-time" />
        <Stat label="Audits today"       value={c.audits_today}       hint="last 24h" />
        <Stat label="This month"         value={c.audits_month}       hint="calendar month" />
        <Stat label="Reports delivered"  value={c.reports}            hint="PDFs generated" />
        <Stat label="Validated patterns" value={c.patterns_doubt_passed} hint="cleared DOUBT" />
        <Stat label="Teams"              value={c.teams}              hint="active" />
        <Stat label="Companies"          value={c.companies ?? 0}     hint="active" />
        <Stat label="Events 24h"         value={c.events_24h}         hint="events_log" />
      </section>

      {/* Time series: audits + reports per day */}
      <Card title={`Audits and reports - ${rangeLabel}`}>
        <div style={{ width: "100%", height: 260 }}>
          <ResponsiveContainer>
            <AreaChart data={series} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="ga" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"  stopColor="#1B8A4F" stopOpacity={0.45} />
                  <stop offset="100%" stopColor="#1B8A4F" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gr" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"  stopColor="#3B82F6" stopOpacity={0.45} />
                  <stop offset="100%" stopColor="#3B82F6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--colour-separator)" strokeDasharray="2 4" />
              <XAxis dataKey="day" stroke="var(--colour-label-tertiary)" fontSize={11} tickFormatter={(d) => d.slice(5)} />
              <YAxis stroke="var(--colour-label-tertiary)" fontSize={11} />
              <Tooltip cursor={{ stroke: "var(--colour-accent)", strokeWidth: 1 }} />
              <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
              <Area type="monotone" dataKey="n_audits"  stroke="#1B8A4F" fill="url(#ga)" name="Audits" />
              <Area type="monotone" dataKey="n_reports" stroke="#3B82F6" fill="url(#gr)" name="Reports" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Three-up: dimension health + cohort mean over time + funnel */}
      <section style={{ display: "grid", gridTemplateColumns: "1fr 1.3fr 0.9fr", gap: "var(--space-4)" }}>
        <DimHealthCard dims={dims} nScored={dims.n_scored} rangeLabel={rangeLabel} />

        <Card title={`Cohort average score - ${rangeLabel}`}>
          <div style={{ width: "100%", height: 240 }}>
            <ResponsiveContainer>
              <LineChart data={series} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--colour-separator)" strokeDasharray="2 4" />
                <XAxis dataKey="day" stroke="var(--colour-label-tertiary)" fontSize={11} tickFormatter={(d) => d.slice(5)} />
                <YAxis stroke="var(--colour-label-tertiary)" fontSize={11} domain={[0, 100]} />
                <Tooltip />
                <Line type="monotone" dataKey="mean_overall" stroke="#1B8A4F" strokeWidth={2} dot={false} name="Mean overall /100" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title={`Funnel - ${rangeLabel}`}>
          <div style={{ width: "100%", height: 240 }}>
            <ResponsiveContainer>
              <BarChart data={funnel?.stages ?? []} layout="vertical" margin={{ top: 10, right: 20, left: 60, bottom: 0 }}>
                <CartesianGrid stroke="var(--colour-separator)" strokeDasharray="2 4" />
                <XAxis type="number" stroke="var(--colour-label-tertiary)" fontSize={11} />
                <YAxis type="category" dataKey="label" stroke="var(--colour-label-tertiary)" fontSize={11} width={110} />
                <Tooltip />
                <Bar dataKey="n" fill="#1B8A4F" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </section>

      {/* Two-up: regions + top archetypes */}
      <section style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)" }}>
        <Card title="Reps by Region">
        {regions.length > 0 ? (
          <div style={{ width: "100%", height: 240 }}>
            <ResponsiveContainer>
              <BarChart data={regions}>
                <CartesianGrid stroke="var(--colour-separator)" strokeDasharray="2 4" />
                <XAxis dataKey="region" stroke="var(--colour-label-tertiary)" fontSize={11} />
                <YAxis stroke="var(--colour-label-tertiary)" fontSize={11} />
                <Tooltip />
                <Bar dataKey="reps" fill="#1B8A4F" name="Reps" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="hig-footnote" style={{ color: "var(--colour-label-secondary)", margin: 0 }}>No teams created yet — reps will appear here once teams exist.</p>
        )}
      </Card>
        <Card title="Top Archetypes">
        {tops.length > 0 ? (
          <div style={{ width: "100%", height: 240 }}>
            <ResponsiveContainer>
              <BarChart data={tops} layout="vertical" margin={{ top: 10, right: 20, left: 80, bottom: 0 }}>
                <CartesianGrid stroke="var(--colour-separator)" strokeDasharray="2 4" />
                <XAxis type="number" stroke="var(--colour-label-tertiary)" fontSize={11} />
                <YAxis type="category" dataKey="name" stroke="var(--colour-label-tertiary)" fontSize={11} width={130} />
                <Tooltip />
                <Bar dataKey="n" fill="#3B82F6" radius={[0,4,4,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="hig-footnote" style={{ color: "var(--colour-label-secondary)", margin: 0 }}>No archetype assignments yet — this fills in once audits are scored.</p>
        )}
      </Card>
      </section>

      <footer className="hig-footnote">
        Bootstrapped {new Date(boot.served_at).toLocaleString("en-AU")}.
      </footer>
    </div>
  );
}
