import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { Card, SectionEyebrow, Button } from "../components/Card";
import { BandBar } from "../components/BandBar";
import { SortableTable } from "../components/SortableTable";
import { useAuth } from "../auth";

const AU_REGIONS = ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT", "Overseas"];

type Company = { company_id: number; name: string; industry: string | null;
                 contact_name: string | null; contact_email: string | null;
                 contact_mobile: string | null; website: string | null };
type Team = {
  team_id: number;
  name: string;
  role_label: string | null;
  region: string | null;
  n_respondents: number;
  avg_score_100: number | null;
  director: { respondent_id: number; name: string; email: string; mobile: string | null; role: string } | null;
};
type Exec = {
  respondent_id: number; name: string | null; email: string;
  mobile: string | null; role: string; job_title: string | null; team_id: number | null;
};
type Payload = { company: Company; teams: Team[]; execs: Exec[] };

type BiggestGap = { trait: string; score_100: number; band: string } | null;
type Overview = {
  company: Company;
  month_label: string;
  n_teams: number;
  n_respondents: number;
  company_average_score_100: number | null;
  elite_performers: number;
  at_risk_reps: number;
  biggest_gap: BiggestGap;
};
type DistRow = {
  dimension: string;
  dimension_label: string;
  elite: number;
  performing: number;
  practising: number;
  developing: number;
};
type Distribution = { company_id: number; total: number; distribution: DistRow[] };

export default function CompanyDetail() {
  const { companyId } = useParams();
  const id = Number(companyId);
  const [params] = useSearchParams();
  const [data, setData] = useState<Payload | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [dist, setDist] = useState<Distribution | null>(null);
  const [adding, setAdding] = useState(params.get("add") === "team");
  const [creatingLink, setCreatingLink] = useState(false);
  const [copied, setCopied] = useState(false);

  async function ensureTeamAndCopy() {
    let teamId = data?.teams[0]?.team_id;
    if (!teamId) {
      setCreatingLink(true);
      try {
        const res = await api<{ ok: boolean; team_id: number }>("/api/teams", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: "All Employees", company_id: id }),
        });
        teamId = res.team_id;
        const refreshed = await api<Payload>(`/api/companies/${id}/teams`);
        setData(refreshed);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to create invite link. Please try again.");
        setCreatingLink(false);
        return;
      }
      setCreatingLink(false);
    }
    const link = `${window.location.origin}/take-audit?team=${teamId}`;
    await navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const { me } = useAuth();
  const [t, setT] = useState({ name: "", region: "NSW", role_label: "Sales Director", contact_name: "", contact_email: "", contact_mobile: "" });

  function refresh() {
    setError(null);
    api<Payload>(`/api/companies/${id}/teams`).then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load company. Please try again."));
    api<Overview>(`/api/companies/${id}/overview`).then(setOverview).catch(() => {});
    api<Distribution>(`/api/companies/${id}/distribution`).then(setDist).catch(() => {});
  }
  useEffect(() => { refresh(); }, [id]);

  async function create() {
    if (!t.name.trim()) return;
    setBusy(true);
    try {
      await api("/api/teams", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: t.name.trim(), company_id: id,
          role_label: t.role_label, region: t.region,
          contact_name: t.contact_name || null,
          contact_email: t.contact_email || null,
          contact_mobile: t.contact_mobile || null,
        }),
      });
      setAdding(false);
      setT({ name: "", region: "NSW", role_label: "Sales Director", contact_name: "", contact_email: "", contact_mobile: "" });
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create team. Please try again.");
    } finally { setBusy(false); }
  }

  if (error) return (
    <p className="hig-caption-1" style={{ color: "#D92D20" }}>
      {error}
    </p>
  );
  if (!data) return <p className="hig-footnote">Loading...</p>;
  const c = data.company;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)", maxWidth: 1100 }}>
      <header>
        <div className="hig-footnote">
          <Link to="/companies" style={{ color: "var(--colour-accent)" }}>Companies</Link>
          {" · "}
          <span>{c.industry ?? "-"}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginTop: "var(--space-1)" }}>
          <h1 className="hig-large-title" style={{ margin: 0, fontWeight: 700 }}>
            {c.name.replace(/^Demo:\s*/, "")}
          </h1>
          {c.name.startsWith("Demo:") && (
            <span className="hig-caption-1" style={{
              background: "var(--colour-accent-tint-bg)", color: "var(--colour-accent)",
              padding: "3px 10px", borderRadius: 999, fontWeight: 700,
              textTransform: "uppercase", letterSpacing: "0.06em",
            }}>Demo</span>
          )}
        </div>
        <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-2)" }}>
          {data.teams.length} teams · {overview?.n_respondents ?? data.teams.reduce((n, tm) => n + tm.n_respondents, 0)} reps under this company.
          Click a team to drop into the director-scoped executive view.
        </p>
      </header>

      <Card title="Employee invite link">
        <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginBottom: "var(--space-3)" }}>
          Share this link with anyone at the company. Everyone who completes the audit through it lands in the company dashboard automatically.
        </p>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
          <code style={{ flex: 1, padding: "8px 12px", background: "var(--colour-fill-secondary)", borderRadius: 8, fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {data.teams.length > 0 ? `${window.location.origin}/take-audit?team=${data.teams[0].team_id}` : "No link yet"}
          </code>
          <Button variant="filled" size="md" onClick={ensureTeamAndCopy} disabled={creatingLink}>
            {creatingLink ? "Creating..." : copied ? "Copied!" : data.teams.length > 0 ? "Copy link" : "Get invite link"}
          </Button>
        </div>
      </Card>

      {/* KPI strip — 4 equal, mirrors the team executive view */}
      <section style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "var(--space-4)" }}>
        <KpiCard
          label="Company average score"
          value={overview?.company_average_score_100 ?? "-"}
          suffix="/100"
          hint={`across ${overview?.n_teams ?? data.teams.length} teams`}
        />
        <KpiCard
          label="Elite performers"
          value={overview?.elite_performers ?? "-"}
          hint="85+ across all 4 traits"
          tone="elite"
        />
        <KpiCard
          label="At-risk reps"
          value={overview?.at_risk_reps ?? "-"}
          hint="Developing in 2+ traits"
          tone="risk"
        />
        <KpiCard
          label="Biggest gap"
          value={overview?.biggest_gap?.trait ?? "-"}
          hint={
            overview?.biggest_gap
              ? `${overview.biggest_gap.score_100} /100 · ${overview.biggest_gap.band}`
              : ""
          }
          big={false}
        />
      </section>

      {/* Distribution */}
      <Card>
        <SectionEyebrow>Score distribution by band</SectionEyebrow>
        <h2 className="hig-title-3" style={{ margin: "var(--space-1) 0 var(--space-3) 0" }}>
          How the {overview?.n_respondents ?? "…"} reps split per trait
        </h2>
        <p className="hig-callout" style={{ color: "var(--colour-label-secondary)", marginTop: 0, marginBottom: "var(--space-4)" }}>
          Each bar shows how reps across every team in this company are distributed across the 4 performance bands per trait.
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

      {/* Company main contacts (CEO / HR / L&D / Sales Directors) */}
      <Card title="Executives and Sales Managers">
        {data.execs.length === 0 ? (
          <p className="hig-footnote" style={{ margin: 0 }}>
            No execs or sales managers attached to this company yet. Add via Settings → Users & Roles.
          </p>
        ) : (
          <div style={{ display: "grid",
                        gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
                        gap: "var(--space-3)" }}>
            {data.execs.map((e) => (
              <Link key={e.respondent_id} to={`/respondents/${e.respondent_id}`}
                style={{ background: "var(--colour-bg-system)",
                         border: "1px solid var(--colour-separator-opaque)",
                         borderRadius: "var(--radius-md)",
                         padding: "var(--space-3)",
                         display: "flex", alignItems: "center", gap: "var(--space-3)",
                         color: "var(--colour-label)", textDecoration: "none" }}>
                <span style={{ width: 36, height: 36, borderRadius: "50%",
                               background: roleColour(e.role), color: "#fff",
                               display: "flex", alignItems: "center", justifyContent: "center",
                               fontWeight: 700, fontSize: 14, textTransform: "uppercase" }}>
                  {(e.name ?? e.email).slice(0, 1).toUpperCase()}
                </span>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div className="hig-headline" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {e.name ?? e.email}
                  </div>
                  <div className="hig-caption-1" style={{ color: "var(--colour-label-secondary)",
                                                            textTransform: "capitalize" }}>
                    {e.role.replace("_", " ")}{e.job_title ? ` · ${e.job_title}` : ""}
                  </div>
                  <div className="hig-caption-1" style={{ color: "var(--colour-label-tertiary)",
                                                            overflow: "hidden", textOverflow: "ellipsis",
                                                            whiteSpace: "nowrap" }}>
                    {e.email}{e.mobile ? ` · ${e.mobile}` : ""}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </Card>

      {/* Teams */}
      <Card title="Teams"
        action={
          <Button variant="filled" size="md" onClick={() => setAdding((v) => !v)}>
            {adding ? "Cancel" : "Add team +"}
          </Button>
        }>
        {adding && (
          <div style={{ marginBottom: "var(--space-4)", padding: "var(--space-4)",
                        background: "var(--colour-bg-system)",
                        border: "1px solid var(--colour-separator-opaque)",
                        borderRadius: "var(--radius-md)" }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "var(--space-3)" }}>
              <Field label="Team name" value={t.name} onChange={(v) => setT({ ...t, name: v })}
                     placeholder="e.g. Hospital Field Sales" />
              <SelectField label="Region" value={t.region} onChange={(v) => setT({ ...t, region: v })}
                           options={AU_REGIONS.map(r => ({ value: r, label: r }))} />
              <Field label="Role label" value={t.role_label} onChange={(v) => setT({ ...t, role_label: v })}
                     placeholder="Sales Director" />
              <Field label="Contact name" value={t.contact_name} onChange={(v) => setT({ ...t, contact_name: v })}
                     placeholder="Primary contact" />
              <Field label="Contact email" value={t.contact_email} onChange={(v) => setT({ ...t, contact_email: v })}
                     placeholder="contact@team.com" />
              <Field label="Mobile" value={t.contact_mobile} onChange={(v) => setT({ ...t, contact_mobile: v })}
                     placeholder="04xx xxx xxx" />
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end",
                          gap: "var(--space-2)", marginTop: "var(--space-3)",
                          paddingTop: "var(--space-3)", borderTop: "1px solid var(--colour-separator)" }}>
              <Button variant="plain" size="md" onClick={() => setAdding(false)}>Cancel</Button>
              <Button variant="filled" size="md" onClick={create}>{busy ? "Saving..." : "Create team"}</Button>
            </div>
          </div>
        )}
        <SortableTable<Team>
          rows={data.teams}
          rowKey={(tm) => tm.team_id}
          initialSort={{ key: "avg_score_100", dir: "desc" }}
          empty={<p className="hig-footnote" style={{ margin: 0 }}>No teams yet — add the first one above.</p>}
          columns={[
            { key: "name", label: "Team", format: (tm) => (
                <Link to={`/teams/${tm.team_id}`} style={{ color: "var(--colour-label)", textDecoration: "none", fontWeight: 600 }}>
                  {tm.name}
                </Link>
              ) },
            { key: "role_label", label: "Role", format: (tm) => tm.role_label ?? "-" },
            { key: "region", label: "Region", format: (tm) => tm.region ?? "-" },
            { key: "n_respondents", label: "Reps", align: "right" },
            { key: "avg_score_100", label: "Avg score", align: "right",
              format: (tm) => tm.avg_score_100 != null ? `${tm.avg_score_100}/100` : "-" },
            { key: "director", label: "Director", sortable: false,
              format: (tm) => tm.director ? tm.director.name : "-" },
          ]}
        />
      </Card>

      <Card title="Company-Wide Scoping" data-noop="">
        <p className="hig-callout" style={{ color: "var(--colour-label-secondary)", margin: 0 }}>
          Every aggregate on this page is filtered by <code>company_id = {id}</code>.
          No data from other companies leaks in. Team-level views drill in further
          and never see data from sibling teams.
        </p>
      </Card>
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

const inputStyle = {
  padding: "var(--space-2) var(--space-3)",
  borderRadius: "var(--radius-md)",
  border: "1px solid var(--colour-separator-opaque)",
  background: "var(--colour-bg-system-secondary)",
  color: "var(--colour-label)",
  font: "inherit",
  width: "100%",
};

function Field(
  { label, value, onChange, placeholder }:
  { label: string; value: string; onChange: (v: string) => void; placeholder?: string }
) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span className="hig-caption-1">{label}</span>
      <input value={value} placeholder={placeholder}
             onChange={(e) => onChange(e.target.value)}
             style={inputStyle} />
    </label>
  );
}
function SelectField(
  { label, value, onChange, options }:
  { label: string; value: string; onChange: (v: string) => void;
    options: { value: string; label: string }[] }
) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span className="hig-caption-1">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}
              style={inputStyle}>
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
}
function roleColour(role: string): string {
  switch (role) {
    case "ceo":                   return "var(--colour-system-purple)";
    case "hr":                    return "var(--colour-system-pink)";
    case "learning_development":  return "var(--colour-system-indigo)";
    case "sales_director":        return "var(--colour-accent)";
    default:                      return "var(--colour-label-tertiary)";
  }
}
