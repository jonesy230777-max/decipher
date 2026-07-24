import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Card, SectionEyebrow } from "../components/Card";
import { BandBar } from "../components/BandBar";

type Team = { team_id: number; name: string; company_id: number | null; n_respondents: number };
type Company = { company_id: number; name: string };
type Person = {
  respondent_id: number; name: string | null; email: string;
  role: string; team_name: string | null; latest_overall: number | null;
};
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
  const [teams, setTeams] = useState<Team[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [companyFilter, setCompanyFilter] = useState<string>("");
  const [teamFilter, setTeamFilter] = useState<string>("");
  const [people, setPeople] = useState<Person[] | null>(null);

  useEffect(() => {
    api<{ teams: Team[] }>("/api/teams").then((d) => setTeams(d.teams));
    api<{ companies: Company[] }>("/api/companies").then((d) => setCompanies(d.companies));
    api<{ patterns: Pattern[] }>("/api/cohort/patterns").then((d) => setPatterns(d.patterns));
  }, []);

  useEffect(() => {
    const p = new URLSearchParams();
    if (companyFilter) p.set("company_id", companyFilter);
    if (teamFilter)    p.set("team_id", teamFilter);
    const qs = p.toString() ? `?${p}` : "";
    api<Stats>(`/api/cohort/stats${qs}`).then(setStats);
    if (teamFilter) {
      api<{ people: Person[] }>(`/api/people?team_id=${teamFilter}`).then((d) => setPeople(d.people));
    } else {
      setPeople(null);
    }
  }, [companyFilter, teamFilter]);

  const teamsForCompany = useMemo(() => {
    if (!companyFilter) return teams;
    return teams.filter((t) => String(t.company_id) === companyFilter);
  }, [teams, companyFilter]);

  const scopeLabel = teamFilter
    ? teams.find((t) => String(t.team_id) === teamFilter)?.name
    : companyFilter
      ? companies.find((c) => String(c.company_id) === companyFilter)?.name.replace(/^Demo:\s*/, "")
      : "All companies and teams";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)", maxWidth: 1400 }}>
      <header>
        <h1 className="hig-large-title" style={{ margin: 0 }}>Cohort Insights</h1>
        <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-2)" }}>
          Aggregate across <strong>{scopeLabel}</strong>. Filter to a company, drill into a team, then click a person to open their profile.
        </p>
      </header>

      {/* Cascading filters */}
      <Card>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "var(--space-3)" }}>
          <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span className="hig-caption-1">Company</span>
            <select value={companyFilter}
                    onChange={(e) => { setCompanyFilter(e.target.value); setTeamFilter(""); }}
                    style={inputStyle}>
              <option value="">All companies</option>
              {companies.map((c) => (
                <option key={c.company_id} value={c.company_id}>{c.name.replace(/^Demo:\s*/, "")}</option>
              ))}
            </select>
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span className="hig-caption-1">Team</span>
            <select value={teamFilter} onChange={(e) => setTeamFilter(e.target.value)}
                    style={inputStyle}>
              <option value="">All teams{companyFilter ? " in this company" : ""}</option>
              {teamsForCompany.map((t) => (
                <option key={t.team_id} value={t.team_id}>{t.name} ({t.n_respondents})</option>
              ))}
            </select>
          </label>
        </div>
      </Card>

      {stats?.totals && (
        <Card title="Cohort Means">
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

      {stats && !stats.totals && (
        <Card title="Cohort Means">
          <p className="hig-footnote" style={{ color: "var(--colour-label-secondary)", margin: 0 }}>No scored audits yet in this scope.</p>
        </Card>
      )}

      <Card title="Distribution by Band, Every Dimension">
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

      <Card title="Trailing 14-Day Means">
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
      {stats && stats.trend.length === 0 && (
        <p className="hig-footnote" style={{ color: "var(--colour-label-secondary)", margin: 0 }}>No trend data yet — this fills in after the first nightly snapshot runs.</p>
      )}
      </Card>

      {/* People in this team (when scoped to a team) */}
      {people && (
        <Card title={`People in ${scopeLabel} (${people.length})`}>
          {people.length === 0 ? (
            <p className="hig-footnote" style={{ margin: 0 }}>No people in this scope.</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {people.slice(0, 50).map((p, i) => (
                <li key={p.respondent_id}
                    style={{
                      padding: "var(--space-2) 0",
                      borderTop: i === 0 ? "none" : "1px solid var(--colour-separator)",
                      display: "flex", alignItems: "center", gap: "var(--space-3)",
                    }}>
                  <Link to={`/respondents/${p.respondent_id}`}
                        style={{ color: "var(--colour-accent)", fontWeight: 600,
                                 textDecoration: "none", flex: 1 }}>
                    {p.name ?? p.email}
                  </Link>
                  <span className="hig-footnote" style={{ color: "var(--colour-label-secondary)" }}>
                    {p.role.replace("_", " ")}
                  </span>
                  <span className="hig-callout hig-numeric"
                        style={{ width: 60, textAlign: "right" }}>
                    {p.latest_overall != null ? `${(p.latest_overall * 100).toFixed(0)} /100` : "·"}
                  </span>
                </li>
              ))}
              {people.length > 50 && (
                <li className="hig-footnote" style={{ marginTop: "var(--space-2)", color: "var(--colour-label-tertiary)" }}>
                  Showing first 50 of {people.length}.
                </li>
              )}
            </ul>
          )}
        </Card>
      )}

      <Card
        title="Validated Patterns"
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

const inputStyle: React.CSSProperties = {
  height: 36, padding: "0 var(--space-3)",
  border: "1px solid var(--colour-separator-opaque)",
  borderRadius: "var(--radius-sm)",
  background: "var(--colour-bg-system)",
  color: "var(--colour-label)",
  fontSize: "var(--type-callout)", fontFamily: "inherit",
  width: "100%", boxSizing: "border-box",
};
