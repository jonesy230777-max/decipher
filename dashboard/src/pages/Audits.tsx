import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { SortableTable, type Column } from "../components/SortableTable";
import { Button, Card } from "../components/Card";

type Audit = {
  audit_id: number;
  status: "in_progress" | "completed" | "scored" | "reported" | "failed_quality_gate";
  started_at: string;
  completed_at: string | null;
  email: string;
  respondent_name: string | null;
  company: string | null;
  industry: string | null;
  team_id: number | null;
  team_name: string | null;
  cognitive_empathy: number | null;
  eq: number | null;
  pressure_composure: number | null;
  storytelling: number | null;
  archetype_code: string | null;
  archetype_name: string | null;
  archetype_confidence: number | null;
  report_id: number | null;
  audit_version_code: string | null;
  audit_version_name: string | null;
};

type Team = {
  team_id: number;
  name: string;
  n_respondents: number;
  region: string | null;
  company_id: number | null;
  company_name: string | null;
};

type Company = { company_id: number; name: string };

const STATUS_COLOUR: Record<Audit["status"], string> = {
  in_progress: "var(--colour-label-tertiary)",
  completed:   "var(--colour-system-blue)",
  scored:      "var(--colour-system-blue)",
  reported:    "var(--colour-system-green)",
  failed_quality_gate: "var(--colour-system-red)",
};

const AU_REGIONS = ["NSW","VIC","QLD","WA","SA","TAS","ACT","NT","Overseas"];
const fmtPct = (v: number | null) =>
  v === null || v === undefined ? "·" : `${(v * 100).toFixed(0)}`;

export default function Audits() {
  const [rows, setRows] = useState<Audit[] | null>(null);
  const [teams, setTeams] = useState<Team[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [companyFilter, setCompanyFilter] = useState<string>("");
  const [teamFilter, setTeamFilter]       = useState<string>("");
  const [statusFilter, setStatusFilter]   = useState<string>("");
  const [regionFilter, setRegionFilter]   = useState<string>("");
  const [versionFilter, setVersionFilter] = useState<string>("");
  const [q, setQ]                         = useState<string>("");

  useEffect(() => {
    api<{ teams: Team[] }>("/api/teams").then((d) => setTeams(d.teams));
    api<{ companies: Company[] }>("/api/companies").then((d) => setCompanies(d.companies));
  }, []);

  useEffect(() => {
    const parts: string[] = [];
    if (statusFilter)  parts.push(`status=${statusFilter}`);
    if (teamFilter)    parts.push(`team_id=${teamFilter}`);
    if (versionFilter) parts.push(`version=${versionFilter}`);
    const qs = parts.length ? `?${parts.join("&")}` : "";
    api<{ audits: Audit[] }>(`/api/audits${qs}`).then((d) => setRows(d.audits));
  }, [statusFilter, teamFilter, versionFilter]);

  // Cascade: when a company is picked, narrow the team dropdown to its teams.
  const teamsForCompany = useMemo(() => {
    if (!companyFilter) return teams;
    return teams.filter((t) => String(t.company_id) === companyFilter);
  }, [teams, companyFilter]);

  // Client-side: region + search + company-derived constraints.
  const visible = useMemo(() => {
    if (!rows) return null;
    return rows.filter((a) => {
      if (companyFilter) {
        const t = teams.find((tt) => tt.team_id === a.team_id);
        if (!t || String(t.company_id) !== companyFilter) return false;
      }
      if (regionFilter) {
        const t = teams.find((tt) => tt.team_id === a.team_id);
        if (!t || t.region !== regionFilter) return false;
      }
      if (q.trim()) {
        const needle = q.trim().toLowerCase();
        const hay = `${a.respondent_name ?? ""} ${a.email}`.toLowerCase();
        if (!hay.includes(needle)) return false;
      }
      return true;
    });
  }, [rows, companyFilter, regionFilter, q, teams]);

  const counts = visible
    ? visible.reduce<Record<string, number>>((acc, a) => {
        acc[a.status] = (acc[a.status] ?? 0) + 1;
        return acc;
      }, {})
    : {};

  const columns: Column<Audit>[] = [
    { key: "audit_id", label: "ID",
      style: { fontVariantNumeric: "tabular-nums", width: 56 } },
    {
      key: "respondent_name", label: "Respondent",
      sortValue: (a) => (a.respondent_name ?? a.email ?? "").toLowerCase(),
      format: (a) => (
        <>
          <div style={{ fontWeight: 600 }}>{a.respondent_name ?? a.email}</div>
          <div className="hig-caption-1" style={{ color: "var(--colour-label-secondary)" }}>{a.email}</div>
        </>
      ),
    },
    {
      key: "team_name", label: "Team",
      format: (a) => a.team_name
        ? <span className="hig-callout">{a.team_name}</span>
        : <span className="hig-footnote" style={{ color: "var(--colour-label-tertiary)" }}>standalone</span>,
    },
    { key: "industry", label: "Industry" },
    {
      key: "status", label: "Status",
      format: (a) => (
        <span style={{ color: STATUS_COLOUR[a.status], fontWeight: 600, textTransform: "capitalize" }}>
          {a.status.replace("_", " ")}
        </span>
      ),
    },
    {
      key: "audit_version_code", label: "Version",
      sortValue: (a) => a.audit_version_code ?? "",
      format: (a) => <VersionPill code={a.audit_version_code} />,
    },
    { key: "cognitive_empathy",  label: "CE", align: "right", format: (a) => fmtPct(a.cognitive_empathy),  style: { fontVariantNumeric: "tabular-nums" } },
    { key: "eq",                 label: "EQ", align: "right", format: (a) => fmtPct(a.eq),                 style: { fontVariantNumeric: "tabular-nums" } },
    { key: "pressure_composure", label: "PC", align: "right", format: (a) => fmtPct(a.pressure_composure), style: { fontVariantNumeric: "tabular-nums" } },
    { key: "storytelling",       label: "ST", align: "right", format: (a) => fmtPct(a.storytelling),       style: { fontVariantNumeric: "tabular-nums" } },
    { key: "archetype_name",     label: "Archetype" },
    {
      key: "started_at", label: "Started",
      format: (a) => (
        <span style={{ color: "var(--colour-label-tertiary)" }}>
          {new Date(a.started_at).toLocaleDateString("en-AU")}
        </span>
      ),
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      <header style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "var(--space-4)" }}>
        <div>
          <h1 className="hig-large-title" style={{ margin: 0 }}>Audits</h1>
          <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-2)" }}>
            Every audit across every team. <span className="hig-numeric">{visible?.length ?? "…"}</span> rows shown. Filter, sort, drill in.
          </p>
        </div>
        <div style={{ display: "flex", gap: "var(--space-2)" }}>
          <Button variant="tinted" size="md" href="/funnel">Funnel ›</Button>
          <Button variant="filled" size="md" href="/audit/start">New Audit +</Button>
        </div>
      </header>

      {/* Filter card */}
      <Card>
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(6, minmax(0, 1fr))",
          gap: "var(--space-3)",
          alignItems: "end",
        }}>
          <Field label="Search">
            <input value={q} onChange={(e) => setQ(e.target.value)}
                   placeholder="name or email"
                   style={inputStyle} />
          </Field>
          <Field label="Company">
            <select value={companyFilter}
                    onChange={(e) => { setCompanyFilter(e.target.value); setTeamFilter(""); }}
                    style={inputStyle}>
              <option value="">All companies</option>
              {companies.map((c) => (
                <option key={c.company_id} value={c.company_id}>{c.name.replace(/^Demo:\s*/, "")}</option>
              ))}
            </select>
          </Field>
          <Field label="Team">
            <select value={teamFilter} onChange={(e) => setTeamFilter(e.target.value)} style={inputStyle}>
              <option value="">All teams</option>
              {teamsForCompany.map((t) => (
                <option key={t.team_id} value={t.team_id}>{t.name} ({t.n_respondents})</option>
              ))}
            </select>
          </Field>
          <Field label="Region">
            <select value={regionFilter} onChange={(e) => setRegionFilter(e.target.value)} style={inputStyle}>
              <option value="">All regions</option>
              {AU_REGIONS.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </Field>
          <Field label="Status">
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={inputStyle}>
              <option value="">All statuses</option>
              <option value="reported">Reported</option>
              <option value="scored">Scored</option>
              <option value="completed">Completed</option>
              <option value="in_progress">In progress</option>
              <option value="failed_quality_gate">Failed quality gate</option>
            </select>
          </Field>
          <Field label="Version">
            <select value={versionFilter} onChange={(e) => setVersionFilter(e.target.value)} style={inputStyle}>
              <option value="">All versions</option>
              <option value="media_sales_v1">Media Sales v1</option>
              <option value="master_v1">Legacy (master v1)</option>
            </select>
          </Field>
        </div>

        {/* Status tally pills row */}
        {visible && (
          <div style={{ display: "flex", gap: "var(--space-2)", marginTop: "var(--space-3)", flexWrap: "wrap" }}>
            {(["reported","scored","completed","in_progress"] as const).map((s) => (
              <span key={s} className="hig-caption-1"
                    style={{
                      background: "var(--colour-fill-quaternary)",
                      borderRadius: 999, padding: "3px 10px",
                      fontWeight: 600,
                      color: STATUS_COLOUR[s],
                    }}>
                {s.replace("_", " ")}: {counts[s] ?? 0}
              </span>
            ))}
            <span className="hig-caption-1"
                  style={{ background: "var(--colour-fill-quaternary)",
                           borderRadius: 999, padding: "3px 10px", fontWeight: 600 }}>
              total: {visible.length}
            </span>
          </div>
        )}
      </Card>

      <SortableTable
        rows={visible}
        columns={columns}
        rowKey={(a) => a.audit_id}
        initialSort={{ key: "started_at", dir: "desc" }}
      />
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
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 0 }}>
      <span className="hig-caption-1">{label}</span>
      {children}
    </label>
  );
}

function VersionPill({ code }: { code: string | null }) {
  if (!code) return <span style={{ color: "var(--colour-label-tertiary)" }}>·</span>;
  const isCurrent = code === "media_sales_v1";
  const bg = isCurrent ? "var(--colour-accent-tint-bg)" : "var(--colour-fill-quaternary)";
  const fg = isCurrent ? "var(--colour-accent)"         : "var(--colour-label-secondary)";
  const label = isCurrent ? "Media Sales v1" : code;
  return (
    <span style={{
      background: bg, color: fg,
      padding: "2px 8px", borderRadius: "var(--radius-pill)",
      fontSize: "var(--type-caption-1)", fontWeight: 600, whiteSpace: "nowrap",
    }}>
      {label}
    </span>
  );
}
