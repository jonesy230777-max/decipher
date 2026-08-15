/**
 * People index. Lists every person across companies + teams with
 * cascading filters (Company → Team) and search. Click-through to
 * /respondents/:id.
 */
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, ROLE_LABEL, type Role } from "../api";
import { Card, Button } from "../components/Card";
import { SortableTable, type Column } from "../components/SortableTable";

type Person = {
  respondent_id: number;
  name: string | null;
  first_name: string | null;
  last_name: string | null;
  email: string;
  mobile: string | null;
  job_title: string | null;
  role: Role;
  team_id: number | null;
  team_name: string | null;
  company_id: number | null;
  company_name: string | null;
  consent_share_individual: boolean;
  n_audits: number;
  last_audit_at: string | null;
  latest_overall: number | null;
};

type Team = { team_id: number; name: string; company_id: number | null; n_respondents: number };
type Company = { company_id: number; name: string };

export default function People() {
  const [people, setPeople] = useState<Person[] | null>(null);
  const [teams, setTeams] = useState<Team[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [companyFilter, setCompanyFilter] = useState<string>("");
  const [teamFilter, setTeamFilter] = useState<string>("");
  const [roleFilter, setRoleFilter] = useState<string>("");
  const [q, setQ] = useState<string>("");
  const [deleting, setDeleting] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    api<{ teams: Team[] }>("/api/teams").then((d) => setTeams(d.teams));
    api<{ companies: Company[] }>("/api/companies").then((d) => setCompanies(d.companies));
  }, []);

  useEffect(() => {
    const p = new URLSearchParams();
    if (companyFilter) p.set("company_id", companyFilter);
    if (teamFilter) p.set("team_id", teamFilter);
    if (roleFilter) p.set("role", roleFilter);
    if (q.trim()) p.set("q", q.trim());
    api<{ people: Person[] }>(`/api/people?${p}`).then((d) => setPeople(d.people));
  }, [companyFilter, teamFilter, roleFilter, q]);

  // Selection is scoped to whatever is currently shown: reset it any time
  // the visible list changes (new filters, initial load, or a post-delete
  // refresh) so stale ids never linger in the selection.
  useEffect(() => {
    setSelectedIds(new Set());
  }, [people]);

  function toggleOne(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    if (!people || people.length === 0) return;
    setSelectedIds((prev) =>
      prev.size === people.length ? new Set() : new Set(people.map((p) => p.respondent_id))
    );
  }

  async function handleDeleteSelected() {
    if (selectedIds.size === 0) return;
    const ids = Array.from(selectedIds);
    const msg = `Delete ${ids.length} ${ids.length === 1 ? "person" : "people"}? This removes them and every audit/report tied to them, permanently.`;
    if (!window.confirm(msg)) return;
    setDeleting(true);
    try {
      await api("/api/admin/respondents/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ respondent_ids: ids }),
      });
      const params = new URLSearchParams();
      if (companyFilter) params.set("company_id", companyFilter);
      if (teamFilter) params.set("team_id", teamFilter);
      if (roleFilter) params.set("role", roleFilter);
      if (q.trim()) params.set("q", q.trim());
      const d = await api<{ people: Person[] }>(`/api/people?${params}`);
      setPeople(d.people);
    } finally {
      setDeleting(false);
    }
  }

  const teamsForCompany = useMemo(() => {
    if (!companyFilter) return teams;
    return teams.filter((t) => String(t.company_id) === companyFilter);
  }, [teams, companyFilter]);

  const ROLES: Role[] = ["admin","ceo","sales_director","hr","learning_development","sales_person"];

  const columns: Column<Person>[] = [
    {
      key: "select",
      label: "",
      sortable: false,
      thStyle: { width: 36 },
      style: { width: 36 },
      format: (p) => (
        <input
          type="checkbox"
          checked={selectedIds.has(p.respondent_id)}
          onChange={() => toggleOne(p.respondent_id)}
          aria-label={p.name ? `Select ${p.name}` : "Select person"}
        />
      ),
    },
    {
      key: "name", label: "Name",
      sortValue: (p) => (p.name ?? "").toLowerCase(),
      format: (p) => (
        <Link to={`/respondents/${p.respondent_id}`}
          style={{ color: "var(--colour-accent)", textDecoration: "none", fontWeight: 700 }}>
          {p.name ?? "(no name)"}
        </Link>
      ),
    },
    {
      key: "email", label: "Email",
      style: { color: "var(--colour-label-secondary)" },
      sortValue: (p) => p.email.toLowerCase(),
    },
    {
      key: "mobile", label: "Mobile",
      style: { color: "var(--colour-label-secondary)", fontVariantNumeric: "tabular-nums" },
      format: (p) => p.mobile ?? "·",
    },
    {
      key: "role", label: "Role",
      format: (p) => ROLE_LABEL[p.role] ?? p.role,
    },
    {
      key: "company_name", label: "Company",
      format: (p) => p.company_name?.replace(/^Demo:\s*/, "") ?? "·",
    },
    {
      key: "team_name", label: "Team",
      format: (p) => p.team_name ?? "·",
    },
    {
      key: "latest_overall", label: "Last Score",
      align: "right",
      style: { fontVariantNumeric: "tabular-nums" },
      format: (p) => p.latest_overall != null ? (p.latest_overall * 100).toFixed(0) : "·",
    },
    {
      key: "n_audits", label: "Audits",
      align: "right",
      style: { fontVariantNumeric: "tabular-nums" },
    },
    {
      key: "last_audit_at", label: "Last Audit",
      format: (p) => p.last_audit_at
        ? new Date(p.last_audit_at).toLocaleDateString("en-AU")
        : "·",
      style: { color: "var(--colour-label-tertiary)" },
    },
  ];

  const allShownSelected = !!people && people.length > 0 && selectedIds.size === people.length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)", maxWidth: 1400 }}>
      <header style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "var(--space-4)" }}>
        <div>
          <h1 className="hig-large-title" style={{ margin: 0 }}>People</h1>
          <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-2)" }}>
            Every person across every company and team. {people?.length ?? "…"} shown. Click a name to drill into their profile and audit history.
          </p>
        </div>
        <div style={{ display: "flex", gap: "var(--space-3)" }}>
          <Button variant="destructive" size="md" onClick={handleDeleteSelected} disabled={deleting || selectedIds.size === 0}>
            {deleting ? "Deleting…" : `Delete Selected${selectedIds.size > 0 ? ` (${selectedIds.size})` : ""}`}
          </Button>
          <Button variant="filled" size="md" href="/settings">Add Person +</Button>
        </div>
      </header>

      <Card>
        <div style={{ display: "grid",
          gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
          gap: "var(--space-3)", alignItems: "end" }}>
          <Field label="Search">
            <input value={q} onChange={(e) => setQ(e.target.value)}
              placeholder="name or email" style={inputStyle} />
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
          <Field label="Role">
            <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} style={inputStyle}>
              <option value="">All roles</option>
              {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
            </select>
          </Field>
        </div>
      </Card>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", cursor: people && people.length > 0 ? "pointer" : "default" }}>
          <input
            type="checkbox"
            checked={allShownSelected}
            onChange={toggleAll}
            disabled={!people || people.length === 0}
          />
          <span className="hig-footnote" style={{ color: "var(--colour-label-secondary)" }}>
            {selectedIds.size > 0 ? `${selectedIds.size} selected` : "Select all shown"}
          </span>
        </label>
      </div>

      <SortableTable
        rows={people}
        columns={columns}
        rowKey={(p) => p.respondent_id}
        initialSort={{ key: "latest_overall", dir: "desc" }}
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
