import { useEffect, useState } from "react";
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line, ResponsiveContainer,
  XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";
import { Stat } from "../components/Stat";
import { Card, SectionEyebrow } from "../components/Card";
import { TimeRange, rangeDays, type TimeRangeKey } from "../components/TimeRange";
import type { Bootstrap } from "../api";
import { api } from "../api";

type Series = { day: string; n_audits: number; n_reports: number; mean_overall: number };
type Funnel = { stages: { key: string; label: string; n: number }[] };
type RegionRow = { region: string; teams: number; reps: number; avg_overall: number };
type TopArch = { name: string; n: number };

export default function MissionControl({ boot }: { boot: Bootstrap | null }) {
  const [series, setSeries] = useState<Series[]>([]);
  const [funnel, setFunnel] = useState<Funnel | null>(null);
  const [regions, setRegions] = useState<RegionRow[]>([]);
  const [tops, setTops] = useState<TopArch[]>([]);
  const [range, setRange] = useState<TimeRangeKey>("30");
  const days = rangeDays(range);
  const rangeLabel = ({
    "7":   "last 7 days",
    "30":  "last 30 days",
    "180": "last 6 months",
    "365": "last 12 months",
    "all": "all time",
  } as const)[range];

  useEffect(() => {
    api<{ series: Series[] }>(`/api/mission/series?days=${days}`).then((d) => setSeries(d.series));
    api<Funnel>(`/api/funnel?days=${days}`).then(setFunnel);
    api<{ regions: RegionRow[] }>("/api/mission/by-region").then((d) => setRegions(d.regions));
    api<{ archetypes: TopArch[] }>("/api/mission/top-archetypes").then((d) => setTops(d.archetypes));
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

      {/* Two-up: cohort mean over time + funnel bars */}
      <section style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: "var(--space-4)" }}>
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
        </Card>
        <Card title="Top Archetypes">
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
        </Card>
      </section>

      <footer className="hig-footnote">
        Bootstrapped {new Date(boot.served_at).toLocaleString("en-AU")}.
      </footer>
    </div>
  );
}
