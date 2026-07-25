import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { Card, SectionEyebrow, Button } from "../components/Card";
import { useAuth } from "../auth";

const AU_REGIONS = ["NSW","VIC","QLD","WA","SA","TAS","ACT","NT","Overseas"];

type Company = { company_id: number; name: string; industry: string | null;
                   contact_name: string | null; contact_email: string | null;
                   contact_mobile: string | null; website: string | null };
type Team = {
  team_id: number;
  name: string;
  role_label: string | null;
  region: string | null;
  n_respondents: number;
  director: { respondent_id: number; name: string; email: string; mobile: string | null; role: string } | null;
};
type Exec = {
  respondent_id: number; name: string | null; email: string;
  mobile: string | null; role: string; job_title: string | null; team_id: number | null;
};
type Payload = { company: Company; teams: Team[]; execs: Exec[] };

export default function CompanyDetail() {
  const { companyId } = useParams();
  const id = Number(companyId);
  const [params] = useSearchParams();
  const [data, setData] = useState<Payload | null>(null);
  const [adding, setAdding] = useState(params.get("add") === "team");
    const [error, setError] = useState<string | null>(null);
const [busy, setBusy] = useState(false);
const { me } = useAuth();
  const [t, setT] = useState({ name: "", region: "NSW", role_label: "Sales Director", contact_name: "", contact_email: "", contact_mobile: "" });

  function refresh() {
        setError(null);
    api<Payload>(`/api/companies/${id}/teams`).then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load company. Please try again."));
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
          <span>{c.industry ?? "·"}</span>
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
          {data.teams.length} teams under this company. Click a team to drop into the
          director-scoped executive view.
        </p>
      </header>

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
                             padding: "var(--space-3) var(--space-4)",
                             textDecoration: "none", color: "var(--colour-label)",
                             display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                <span aria-hidden="true"
                      style={{ width: 36, height: 36, borderRadius: "50%",
                               background: roleColour(e.role), color: "#FFFFFF",
                               display: "inline-flex", alignItems: "center", justifyContent: "center",
                               fontWeight: 700, fontSize: 14, flexShrink: 0 }}>
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

      <Card title="Teams"
            action={<Button variant="filled" size="md" onClick={() => setAdding(v => !v)}>
              {adding ? "Cancel" : "Add team +"}
            </Button>}>
        {adding && (
          <div style={{ marginBottom: "var(--space-4)",
                        padding: "var(--space-4)",
                        background: "var(--colour-bg-system)",
                        border: "1px solid var(--colour-separator-opaque)",
                        borderRadius: "var(--radius-md)" }}>
            <div style={{ display: "grid",
                          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                          gap: "var(--space-3)" }}>
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
                          paddingTop: "var(--space-3)",
                          borderTop: "1px solid var(--colour-separator)" }}>
              <Button variant="plain" size="md" onClick={() => setAdding(false)}>Cancel</Button>
              <Button variant="filled" size="md" onClick={create}>{busy ? "Saving..." : "Create team"}</Button>
            </div>
          </div>
        )}
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {data.teams.map((t, i) => (
            <li
              key={t.team_id}
              style={{
                padding: "var(--space-3) 0",
                borderTop: i === 0 ? "none" : "1px solid var(--colour-separator)",
              }}
            >
              <Link
                to={`/teams/${t.team_id}`}
                style={{
                  display: "flex", alignItems: "center", gap: "var(--space-4)",
                  color: "var(--colour-label)", textDecoration: "none",
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="hig-headline">{t.name}</div>
                  <div className="hig-footnote">{t.role_label} Dashboard</div>
                </div>
                <div className="hig-callout hig-numeric" style={{ color: "var(--colour-label-secondary)" }}>
                  {t.n_respondents} reps
                </div>
                <span aria-hidden="true" style={{ color: "var(--colour-label-tertiary)", fontSize: "var(--type-title-3)" }}>›</span>
              </Link>
            </li>
          ))}
        </ul>
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

function Field({ label, value, onChange, placeholder }:
  { label: string; value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span className="hig-caption-1">{label}</span>
      <input value={value} placeholder={placeholder}
             onChange={(e) => onChange(e.target.value)}
             style={inputStyle} />
    </label>
  );
}
function SelectField({ label, value, onChange, options }:
  { label: string; value: string; onChange: (v: string) => void;
    options: { value: string; label: string }[] }) {
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
    case "ceo":                  return "var(--colour-system-purple)";
    case "hr":                   return "var(--colour-system-pink)";
    case "learning_development": return "var(--colour-system-indigo)";
    case "sales_director":       return "var(--colour-accent)";
    default:                     return "var(--colour-label-tertiary)";
  }
}

const inputStyle: React.CSSProperties = {
  height: 32, padding: "0 var(--space-3)",
  border: "1px solid var(--colour-separator-opaque)",
  borderRadius: "var(--radius-sm)",
  background: "var(--colour-bg-system)",
  color: "var(--colour-label)",
  fontSize: "var(--type-callout)", fontFamily: "inherit",
};
