import { useEffect, useState } from "react";
import { api, ROLE_LABEL, type Bootstrap, type Role } from "../api";
import { useAuth } from "../auth";
import { Card, Button } from "../components/Card";
import { SortableTable, type Column } from "../components/SortableTable";
import { useTheme, type ThemeChoice } from "../theme";

type Level = "none" | "read" | "write" | "both";
type PermissionRow = { role: Role; capability: string; level: Level; relevant: boolean };
type Capability = { key: string; label: string; group: "page" | "action" };
type PermissionsPayload = {
  roles: Role[];
  capabilities: Capability[];
  matrix: PermissionRow[];
  levels: Level[];
};

type UserRow = {
  respondent_id: number;
  email: string;
  name: string | null;
  role: Role;
  team_id: number | null;
  team_name: string | null;
  company_id: number | null;
  company_name: string | null;
  consent_share_individual: boolean;
  created_at: string;
};

type TeamLite  = { team_id: number; name: string; company_name: string | null };
type CompanyLite = { company_id: number; name: string };

const ROLES: Role[] = [
  "admin", "ceo", "sales_director", "hr", "learning_development", "sales_person",
];

const LEVEL_ORDER: Level[] = ["none", "read", "write", "both"];
const LEVEL_LABEL: Record<Level, string> = {
  none: "None", read: "Read", write: "Write", both: "Both",
};
const LEVEL_STYLE: Record<Level, { bg: string; fg: string; symbol: string }> = {
  none:  { bg: "transparent",               fg: "var(--colour-label-tertiary)", symbol: "·" },
  read:  { bg: "var(--colour-system-blue)", fg: "#FFFFFF",                       symbol: "R" },
  write: { bg: "var(--colour-system-orange)", fg: "#FFFFFF",                     symbol: "W" },
  both:  { bg: "var(--colour-system-green)", fg: "#FFFFFF",                      symbol: "RW" },
};

function RolePermissionMatrix() {
  const { me } = useAuth();
  const isAdmin = me?.role === "admin";
  const [data, setData] = useState<PermissionsPayload | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);

  function refresh() {
    api<PermissionsPayload>("/api/permissions").then(setData);
  }
  useEffect(() => { refresh(); }, []);

  async function cycle(row: PermissionRow) {
    if (!isAdmin || !row.relevant) return;
    const idx = LEVEL_ORDER.indexOf(row.level);
    const next = LEVEL_ORDER[(idx + 1) % LEVEL_ORDER.length];
    const key = `${row.role}/${row.capability}`;
    setBusy(key); 
    try {
                  await api(
        `/api/permissions/${row.role}/${encodeURIComponent(row.capability)}`,
                    {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ level: next }),
                    },
      );
            setData((d) => d && ({
                      ...d,
                      matrix: d.matrix.map((m) =>
                                  m.role === row.role && m.capability === row.capability
                                                       ? { ...m, level: next } : m,
                                                   ),
            }));
            setFlash(`${ROLE_LABEL[row.role]} -> ${row.capability} = ${LEVEL_LABEL[next]}`);
    } catch (e) {
            setFlash(`Failed: ${String(e)}`);
    } finally {
            setBusy(null);
            setTimeout(() => setFlash(null), 3500);
    }
  }

  if (!data) return (
    <Card title="Role Permissions">
      <p className="hig-footnote">Loading permissions...</p>
    </Card>
  );

  // Look-up by [role][capability] for cell render
  const cellMap: Record<string, PermissionRow> = {};
  for (const r of data.matrix) cellMap[`${r.role}/${r.capability}`] = r;
  const pageCaps   = data.capabilities.filter((c) => c.group === "page");
  const actionCaps = data.capabilities.filter((c) => c.group === "action");

  return (
    <Card title="Role Permissions">
      <p className="hig-callout" style={{ color: "var(--colour-label-secondary)", marginTop: 0 }}>
        {isAdmin
          ? "Click any cell to cycle through None → Read → Write → Both → None. Cells marked - are not relevant to that role. Admin-only."
          : "Read-only view. Only the Admin role can edit role permissions."}
      </p>
      {flash && (
        <div role="status" className="hig-caption-1"
             style={{ padding: "var(--space-2) var(--space-3)",
                      background: "var(--colour-accent-tint-bg)",
                      color: "var(--colour-accent)",
                      border: "1px solid var(--colour-accent)",
                      borderRadius: "var(--radius-sm)",
                      marginBottom: "var(--space-3)" }}>
          {flash}
        </div>
      )}

      {/* Legend */}
      <div style={{ display: "flex", gap: "var(--space-2)", marginBottom: "var(--space-3)" }}>
        {LEVEL_ORDER.map((l) => (
          <span key={l} className="hig-caption-1"
                style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
            <span style={{
              display: "inline-block", width: 26, height: 18,
              borderRadius: 4,
              background: LEVEL_STYLE[l].bg,
              color: LEVEL_STYLE[l].fg,
              fontWeight: 700, textAlign: "center", lineHeight: "18px",
              border: l === "none" ? "1px solid var(--colour-separator)" : "none",
            }}>{LEVEL_STYLE[l].symbol}</span>
            {LEVEL_LABEL[l]}
          </span>
        ))}
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--type-footnote)" }}>
          <thead>
            <tr>
              <th style={hdrCell}>Page / Action</th>
              {ROLES.map((r) => (
                <th key={r} style={{ ...hdrCell, textAlign: "center" }}>{ROLE_LABEL[r]}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr><td colSpan={ROLES.length + 1}
                    style={{ padding: "var(--space-3) var(--space-2) var(--space-1)",
                             color: "var(--colour-label-tertiary)",
                             textTransform: "uppercase",
                             letterSpacing: "0.06em", fontSize: 10, fontWeight: 700 }}>
              Pages
            </td></tr>
            {pageCaps.map((cap) => (
              <PermissionRowEl key={cap.key} cap={cap} cellMap={cellMap}
                               isAdmin={!!isAdmin} busy={busy} onCycle={cycle} />
            ))}
            <tr><td colSpan={ROLES.length + 1}
                    style={{ padding: "var(--space-4) var(--space-2) var(--space-1)",
                             color: "var(--colour-label-tertiary)",
                             textTransform: "uppercase",
                             letterSpacing: "0.06em", fontSize: 10, fontWeight: 700 }}>
              Actions
            </td></tr>
            {actionCaps.map((cap) => (
              <PermissionRowEl key={cap.key} cap={cap} cellMap={cellMap}
                               isAdmin={!!isAdmin} busy={busy} onCycle={cycle} />
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function PermissionRowEl({ cap, cellMap, isAdmin, busy, onCycle }: {
  cap: Capability;
  cellMap: Record<string, PermissionRow>;
  isAdmin: boolean;
  busy: string | null;
  onCycle: (r: PermissionRow) => void;
}) {
  return (
    <tr style={{ borderBottom: "1px solid var(--colour-separator)" }}>
      <td style={{ padding: "var(--space-2)", fontWeight: 600 }}>{cap.label}</td>
      {ROLES.map((r) => {
        const row = cellMap[`${r}/${cap.key}`];
        if (!row) return <td key={r} style={{ padding: "var(--space-2)", textAlign: "center", color: "var(--colour-label-tertiary)" }}>-</td>;
        if (!row.relevant) {
          return <td key={r}
                     title="Not relevant to this role"
                     style={{ padding: "var(--space-2)", textAlign: "center", color: "var(--colour-label-tertiary)" }}>-</td>;
        }
        const style = LEVEL_STYLE[row.level];
        const key = `${row.role}/${row.capability}`;
        return (
          <td key={r} style={{ padding: "var(--space-2)", textAlign: "center" }}>
            <button
              disabled={!isAdmin || busy === key}
              onClick={() => onCycle(row)}
              title={isAdmin ? `Currently ${LEVEL_LABEL[row.level]} - click to cycle` : LEVEL_LABEL[row.level]}
              style={{
                minWidth: 36, height: 24,
                padding: "0 8px",
                borderRadius: 6,
                border: row.level === "none" ? "1px solid var(--colour-separator)" : "none",
                background: style.bg, color: style.fg,
                fontWeight: 700, fontSize: 11,
                cursor: isAdmin ? "pointer" : "default",
                opacity: busy === key ? 0.5 : 1,
                fontFamily: "inherit",
              }}
            >
              {style.symbol}
            </button>
          </td>
        );
      })}
    </tr>
  );
}

const hdrCell: React.CSSProperties = {
  textAlign: "left", textTransform: "uppercase", letterSpacing: "0.04em",
  color: "var(--colour-label-tertiary)",
  borderBottom: "1px solid var(--colour-separator)",
  padding: "var(--space-2)",
  fontSize: 10, fontWeight: 700,
};

function UsersAndRoles() {
  const [users, setUsers]       = useState<UserRow[] | null>(null);
  const [counts, setCounts]     = useState<{ role: string; n: number }[]>([]);
  const [teams, setTeams]       = useState<TeamLite[]>([]);
  const [companies, setCompanies] = useState<CompanyLite[]>([]);
  const [filterRole, setFilterRole] = useState<string>("");
  const [filterTeam, setFilterTeam] = useState<string>("");
  const [q, setQ]               = useState("");
  const [busy, setBusy]         = useState(false);
  const [showCreate, setShowCreate] = useState(false);

  // new user
  const [nEmail, setNEmail] = useState("");
  const [nName,  setNName]  = useState("");
  const [nRole,  setNRole]  = useState<Role>("sales_person");
  const [nTeam,  setNTeam]  = useState<string>("");
  const [nCompany, setNCompany] = useState<string>("");

  function refresh() {
    const p = new URLSearchParams();
    if (filterRole) p.set("role", filterRole);
    if (filterTeam) p.set("team_id", filterTeam);
    if (q.trim()) p.set("q", q.trim());
    api<{ users: UserRow[]; counts_by_role: { role: string; n: number }[] }>(`/api/users?${p}`)
      .then((d) => { setUsers(d.users); setCounts(d.counts_by_role); });
  }

  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, [filterRole, filterTeam]);
  useEffect(() => {
    api<{ teams: TeamLite[] }>("/api/teams").then((d) => setTeams(d.teams));
    api<{ companies: CompanyLite[] }>("/api/companies").then((d) => setCompanies(d.companies));
  }, []);

  async function patchRole(u: UserRow, role: Role) {
    if (role === u.role) return;
    setBusy(true);
    try {
      await api(`/api/users/${u.respondent_id}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      });
      refresh();
    } finally { setBusy(false); }
  }
  async function patchTeam(u: UserRow, teamIdStr: string) {
    const v = teamIdStr ? Number(teamIdStr) : null;
    if (v === u.team_id) return;
    setBusy(true);
    try {
      await api(`/api/users/${u.respondent_id}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ team_id: v }),
      });
      refresh();
    } finally { setBusy(false); }
  }
  async function patchConsent(u: UserRow, value: boolean) {
    setBusy(true);
    try {
      await api(`/api/users/${u.respondent_id}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ consent_share_individual: value }),
      });
      refresh();
    } finally { setBusy(false); }
  }
  async function createUser() {
    if (!nEmail.trim()) return;
    setBusy(true);
    try {
      await api("/api/users", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: nEmail.trim(), name: nName.trim() || null, role: nRole,
          team_id: nTeam ? Number(nTeam) : null,
          company_id: nCompany ? Number(nCompany) : null,
        }),
      });
      setNEmail(""); setNName(""); setShowCreate(false);
      refresh();
    } finally { setBusy(false); }
  }

  return (
    <Card title="Users and Roles"
          action={<Button variant="filled" size="md" onClick={() => setShowCreate(v => !v)}>
            {showCreate ? "Cancel" : "Add user +"}
          </Button>}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", marginBottom: "var(--space-3)" }}>
        {counts.map((c) => (
          <span key={c.role}
                className="hig-caption-1"
                style={{
                  background: "var(--colour-fill-quaternary)",
                  borderRadius: "var(--radius-pill)",
                  padding: "4px 10px",
                  fontWeight: 600,
                }}>
            {ROLE_LABEL[c.role as Role] ?? c.role}: {c.n}
          </span>
        ))}
      </div>

      {showCreate && (
        <div style={{
          background: "var(--colour-bg-system)",
          border: "1px solid var(--colour-separator-opaque)",
          borderRadius: "var(--radius-md)",
          padding: "var(--space-4)",
          marginBottom: "var(--space-4)",
          display: "grid",
          gridTemplateColumns: "1.4fr 1.2fr 1fr 1.2fr 1.2fr auto",
          gap: "var(--space-2)",
          alignItems: "end",
        }}>
          <Field label="Email"   value={nEmail} onChange={setNEmail} placeholder="you@company.com" />
          <Field label="Name"    value={nName}  onChange={setNName}  placeholder="Full name" />
          <Select label="Role" value={nRole} onChange={(v) => setNRole(v as Role)}
                  options={ROLES.map(r => ({ value: r, label: ROLE_LABEL[r] }))} />
          <Select label="Team" value={nTeam} onChange={setNTeam}
                  options={[{ value: "", label: "(none)" }, ...teams.map(t => ({ value: String(t.team_id), label: t.name }))]} />
          <Select label="Company" value={nCompany} onChange={setNCompany}
                  options={[{ value: "", label: "(none)" }, ...companies.map(c => ({ value: String(c.company_id), label: c.name }))]} />
          <Button variant="filled" size="md" onClick={createUser}>Create</Button>
        </div>
      )}

      <div style={{ display: "flex", gap: "var(--space-3)", marginBottom: "var(--space-3)", alignItems: "end" }}>
        <Select label="Role filter" value={filterRole} onChange={setFilterRole}
                options={[{ value: "", label: "All roles" }, ...ROLES.map(r => ({ value: r, label: ROLE_LABEL[r] }))]} />
        <Select label="Team filter" value={filterTeam} onChange={setFilterTeam}
                options={[{ value: "", label: "All teams" }, ...teams.map(t => ({ value: String(t.team_id), label: t.name }))]} />
        <Field label="Search" value={q} onChange={setQ} placeholder="email or name" />
        <Button variant="tinted" size="md" onClick={refresh}>Apply</Button>
      </div>

      <UserRolesTable
        users={users}
        teams={teams}
        busy={busy}
        onPatchRole={patchRole}
        onPatchTeam={patchTeam}
        onPatchConsent={patchConsent}
      />
    </Card>
  );
}

function UserRolesTable({
  users, teams, busy, onPatchRole, onPatchTeam, onPatchConsent,
}: {
  users: UserRow[] | null;
  teams: TeamLite[];
  busy: boolean;
  onPatchRole: (u: UserRow, r: Role) => void;
  onPatchTeam: (u: UserRow, t: string) => void;
  onPatchConsent: (u: UserRow, v: boolean) => void;
}) {
  const visible = users ? users.slice(0, 200) : null;

  const columns: Column<UserRow>[] = [
    {
      key: "name", label: "Name",
      format: (u) => u.name ?? "·",
      sortValue: (u) => (u.name ?? "").toLowerCase(),
    },
    {
      key: "email", label: "Email",
      style: { color: "var(--colour-label-secondary)" },
      sortValue: (u) => u.email.toLowerCase(),
    },
    {
      key: "role", label: "Role",
      format: (u) => (
        <select value={u.role} disabled={busy}
                onChange={(e) => onPatchRole(u, e.target.value as Role)}
                style={selectStyle}>
          {ROLES.map(r => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
        </select>
      ),
      sortValue: (u) => u.role,
    },
    {
      key: "team_name", label: "Team",
      format: (u) => (
        <select value={u.team_id ?? ""} disabled={busy}
                onChange={(e) => onPatchTeam(u, e.target.value)}
                style={selectStyle}>
          <option value="">(none)</option>
          {teams.map(t => <option key={t.team_id} value={t.team_id}>{t.name}</option>)}
        </select>
      ),
      sortValue: (u) => u.team_name ?? "",
    },
    {
      key: "consent_share_individual", label: "Consent",
      format: (u) => (
        <label style={{ display: "inline-flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
          <input type="checkbox" checked={u.consent_share_individual} disabled={busy}
                 onChange={(e) => onPatchConsent(u, e.target.checked)} />
          <span className="hig-caption-1">{u.consent_share_individual ? "Yes" : "No"}</span>
        </label>
      ),
      sortValue: (u) => (u.consent_share_individual ? 1 : 0),
    },
    {
      key: "respondent_id", label: "View",
      format: (u) => (
        <a href={`/respondents/${u.respondent_id}`}
           style={{ color: "var(--colour-accent)", textDecoration: "none", fontWeight: 600 }}>
          View ›
        </a>
      ),
      sortable: false,
    },
  ];

  return (
    <>
      <SortableTable
        rows={visible}
        columns={columns}
        rowKey={(u) => u.respondent_id}
        initialSort={{ key: "name", dir: "asc" }}
      />
      {users && users.length > 200 && (
        <div className="hig-footnote" style={{ marginTop: "var(--space-3)", color: "var(--colour-label-tertiary)" }}>
          Showing first 200 of {users.length}. Narrow by role/team/search.
        </div>
      )}
    </>
  );
}

const selectStyle: React.CSSProperties = {
  height: 30,
  padding: "0 var(--space-2)",
  border: "1px solid var(--colour-separator-opaque)",
  borderRadius: "var(--radius-sm)",
  background: "var(--colour-bg-system)",
  color: "var(--colour-label)",
  fontSize: "var(--type-callout)",
  fontFamily: "inherit",
};

function Field({ label, value, onChange, placeholder }:
  { label: string; value: string; onChange: (s: string) => void; placeholder?: string }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span className="hig-caption-1">{label}</span>
      <input value={value} placeholder={placeholder}
             onChange={(e) => onChange(e.target.value)}
             style={{ ...selectStyle, height: 32 }} />
    </label>
  );
}

function Select({ label, value, onChange, options }:
  { label: string; value: string; onChange: (s: string) => void;
    options: { value: string; label: string }[] }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 140 }}>
      <span className="hig-caption-1">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}
              style={{ ...selectStyle, height: 32 }}>
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
}

export default function Settings({ boot }: { boot: Bootstrap | null }) {
  const [theme, setTheme] = useTheme();
  const options: { value: ThemeChoice; label: string; hint: string }[] = [
    { value: "light", label: "Light", hint: "Force light appearance" },
    { value: "dark",  label: "Dark",  hint: "Force dark appearance" },
    { value: "auto",  label: "Auto",  hint: "Follow system (prefers-color-scheme)" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)", maxWidth: 1200 }}>
      <header>
        <h1 className="hig-large-title" style={{ margin: 0 }}>Settings</h1>
        <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-2)" }}>
          Operator only. Most settings land progressively across milestones.
        </p>
      </header>


      <Card title="Appearance">
        <p className="hig-callout" style={{ color: "var(--colour-label-secondary)", marginTop: 0, marginBottom: "var(--space-4)" }}>
          Choose light, dark, or auto-follow-system.
        </p>
        <div
          role="radiogroup"
          aria-label="Theme"
          style={{
            display: "inline-flex",
            gap: 2,
            background: "var(--colour-fill-tertiary)",
            padding: 2,
            borderRadius: "var(--radius-sm)",
          }}
        >
          {options.map((o) => {
            const active = theme === o.value;
            return (
              <button
                key={o.value}
                role="radio"
                aria-checked={active}
                onClick={() => setTheme(o.value)}
                className="hig-callout"
                style={{
                  padding: "var(--space-2) var(--space-4)",
                  borderRadius: 4,
                  border: "none",
                  background: active ? "var(--colour-bg-system)" : "transparent",
                  color: "var(--colour-label)",
                  fontWeight: active ? 600 : 400,
                  cursor: "pointer",
                  boxShadow: active ? "var(--shadow-1)" : "none",
                  minHeight: 36,
                }}
              >
                {o.label}
              </button>
            );
          })}
        </div>
        <p className="hig-footnote" style={{ marginTop: "var(--space-3)" }}>
          {options.find((o) => o.value === theme)?.hint}
        </p>
      </Card>

      <ScoringEngineCard />

      <Card title="Integrations">
        <p className="hig-footnote" style={{ margin: 0 }}>
          Claude API key, Stripe keys, email provider wired in M4 and M8.
        </p>
      </Card>

      <RolePermissionMatrix />

      <UsersAndRoles />
    </div>
  );
}

type ScoringHealth = {
  active_taxonomy: { taxonomy_id: number; name: string; n_archetypes: number; n_described: number } | null;
  questions_v2: number;
  narratives: Record<string, number>;
  audits: {
    v2_audits: number; v2_scored: number; v2_reports: number;
    reports_delivered: number; orphan_reported: number;
    last_report: string | null; last_delivery: string | null;
  };
  mailpit: { host: string; port: number };
  checked_at: string;
};

function ScoringEngineCard() {
  const [data, setData] = useState<ScoringHealth | null>(null);
  const [err,  setErr]  = useState<string | null>(null);

  function refresh() {
    fetch("/api/health/scoring")
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setErr(String(e)));
  }
  useEffect(refresh, []);

  if (err)  return <Card title="Scoring engine"><p className="hig-footnote" style={{ color: "var(--colour-system-red)" }}>{err}</p></Card>;
  if (!data) return <Card title="Scoring engine"><p className="hig-footnote">Loading…</p></Card>;

  const tax = data.active_taxonomy;
  const orphans = data.audits.orphan_reported;
  const ok = orphans === 0 && (tax?.n_described ?? 0) === (tax?.n_archetypes ?? 0);

  return (
    <Card title="Scoring engine"
          action={<button onClick={refresh} className="hig-callout"
                          style={{ background: "transparent", border: "1px solid var(--colour-separator-opaque)",
                                   padding: "4px 10px", borderRadius: "var(--radius-sm)", cursor: "pointer",
                                   color: "var(--colour-label)" }}>
            Refresh
          </button>}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
                    gap: "var(--space-3)" }}>
        <KV label="Active taxonomy"
            value={tax ? `${tax.name} (#${tax.taxonomy_id})` : "none"} />
        <KV label="Archetypes described"
            value={tax ? `${tax.n_described}/${tax.n_archetypes}` : "·"}
            warn={tax && tax.n_described < tax.n_archetypes} />
        <KV label="Questions (v2)" value={String(data.questions_v2)}
            warn={data.questions_v2 !== 34} />
        <KV label="Orphan reported audits" value={String(orphans)}
            warn={orphans > 0} />

        <KV label="v2 audits"         value={String(data.audits.v2_audits)} />
        <KV label="v2 scored"         value={String(data.audits.v2_scored)} />
        <KV label="v2 reports"        value={String(data.audits.v2_reports)} />
        <KV label="Reports delivered" value={String(data.audits.reports_delivered)} />

        <KV label="Last report"   value={data.audits.last_report   ?? "never"} />
        <KV label="Last delivery" value={data.audits.last_delivery ?? "never"} />
        <KV label="Mailpit" value={`${data.mailpit.host}:${data.mailpit.port}`} />
        <KV label="Status"
            value={ok ? "Healthy" : "Attention"}
            tone={ok ? "ok" : "warn"} />
      </div>

      <div style={{ marginTop: "var(--space-4)", display: "flex", flexWrap: "wrap",
                    gap: "var(--space-2)" }}>
        {Object.entries(data.narratives).map(([dim, n]) => (
          <span key={dim} className="hig-caption-1"
                style={{ background: "var(--colour-fill-quaternary)",
                         borderRadius: "var(--radius-pill)",
                         padding: "3px 10px", fontWeight: 600 }}>
            {dim.replace(/_/g, " ")}: {n}
          </span>
        ))}
      </div>

      <p className="hig-footnote" style={{ marginTop: "var(--space-3)",
            color: "var(--colour-label-tertiary)" }}>
        Snapshot taken {new Date(data.checked_at).toLocaleString("en-AU")}.
      </p>
    </Card>
  );
}

function KV({ label, value, warn, tone }: {
  label: string; value: string; warn?: boolean | null; tone?: "ok" | "warn";
}) {
  const isWarn = warn || tone === "warn";
  const isOk   = tone === "ok";
  const colour = isWarn ? "var(--colour-system-orange)"
                : isOk  ? "var(--colour-system-green)"
                        : "var(--colour-label)";
  return (
    <div>
      <div className="hig-caption-1" style={{ color: "var(--colour-label-secondary)",
              textTransform: "uppercase", letterSpacing: "0.04em" }}>
        {label}
      </div>
      <div className="hig-headline hig-numeric" style={{ marginTop: 2, color: colour }}>{value}</div>
    </div>
  );
}
