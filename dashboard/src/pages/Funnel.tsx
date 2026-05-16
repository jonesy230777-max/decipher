/**
 * Funnel page: invite -> open -> start -> complete -> score -> report.
 *
 * Only Admin / Sales Director / HR / Learning & Development can send
 * invites. CEO is read-only. Sales Person can take the audit but not
 * send. Backend enforces; UI hides the action for ineligible roles.
 */
import { useEffect, useState } from "react";
import { api, ROLE_LABEL, type Bootstrap, type Role } from "../api";
import { Card, SectionEyebrow, Button } from "../components/Card";
import { TimeRange, rangeDays, type TimeRangeKey } from "../components/TimeRange";

const INVITE_ROLES: Role[] = ["admin", "sales_director", "hr", "learning_development"];

type Stage = { key: string; label: string; n: number };
type Invite = {
  invite_id: number;
  email: string;
  first_name: string | null;
  last_name: string | null;
  team_id: number | null;
  company_id: number | null;
  sent_at: string;
  expires_at: string;
  accepted_at: string | null;
  audit_id: number | null;
  invited_by_email: string | null;
};
type FunnelData = {
  stages: Stage[];
  invite_roles: string[];
  recent_invites: Invite[];
  team_id: number | null;
  company_id: number | null;
  days: number;
};
type TeamLite = { team_id: number; name: string; company_name: string | null };

export default function Funnel({ boot }: { boot: Bootstrap | null }) {
  const me = boot?.me ?? null;
  const canSend = me ? INVITE_ROLES.includes(me.role) : false;
  const [data, setData] = useState<FunnelData | null>(null);
  const [teams, setTeams] = useState<TeamLite[]>([]);
  const [teamFilter, setTeamFilter] = useState<string>("");
  const [range, setRange] = useState<TimeRangeKey>("30");
  const days = rangeDays(range);

  // single-invite form
  const [email, setEmail] = useState("");
  const [first, setFirst] = useState("");
  const [last, setLast]   = useState("");
  const [busy, setBusy]   = useState(false);
  const [flash, setFlash] = useState<string | null>(null);

  function refresh() {
    const p = new URLSearchParams({ days: String(days) });
    if (teamFilter) p.set("team_id", teamFilter);
    api<FunnelData>(`/api/funnel?${p}`).then(setData);
  }
  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, [teamFilter, days]);
  useEffect(() => {
    api<{ teams: TeamLite[] }>("/api/teams").then((d) => setTeams(d.teams));
  }, []);

  async function sendOne() {
    if (!email.trim() || !canSend) return;
    setBusy(true);
    try {
      const r = await fetch("/api/audit/invite", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          first_name: first.trim() || null,
          last_name: last.trim() || null,
          team_id: teamFilter ? Number(teamFilter) : null,
          invited_by_email: me?.email,
        }),
      });
      if (!r.ok) {
        const t = await r.text();
        setFlash(`Failed: ${r.status} ${t}`);
      } else {
        const json = await r.json();
        setFlash(json.delivered
          ? `Invite delivered to ${email} (link: ${json.link}).`
          : `Recorded but SMTP failed: ${json.error}`);
        setEmail(""); setFirst(""); setLast("");
      }
      refresh();
      setTimeout(() => setFlash(null), 6000);
    } finally { setBusy(false); }
  }

  async function sendBulk() {
    if (!canSend) return;
    if (!confirm(`Invite every unaudited rep ${teamFilter ? `in this team` : "across all teams"}?`)) return;
    setBusy(true);
    try {
      const r = await fetch("/api/audit/invite/bulk", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          team_id: teamFilter ? Number(teamFilter) : null,
          invited_by_email: me?.email,
        }),
      });
      const json = await r.json();
      setFlash(`Sent ${json.sent} invites (${json.failed} failed) across ${json.targets} unaudited reps.`);
      refresh();
      setTimeout(() => setFlash(null), 6000);
    } finally { setBusy(false); }
  }

  if (!data) return <p className="hig-footnote">Loading funnel...</p>;

  const max = Math.max(1, ...data.stages.map((s) => s.n));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)", maxWidth: 1400 }}>
      <header>
        <h1 className="hig-large-title" style={{ margin: 0 }}>Funnel</h1>
        <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-2)" }}>
          Track every respondent from invite to report. {me ? `You are signed in as ${ROLE_LABEL[me.role]}. ` : ""}
          {canSend
            ? "You can send invites."
            : `Only ${data.invite_roles.map(r => ROLE_LABEL[r as Role] ?? r).join(", ")} can send invites.`}
        </p>
      </header>

      {flash && (
        <div role="status" className="hig-callout"
             style={{ padding: "var(--space-3) var(--space-4)",
                      background: "var(--colour-accent-tint-bg)",
                      color: "var(--colour-accent)",
                      border: "1px solid var(--colour-accent)",
                      borderRadius: "var(--radius-md)" }}>
          {flash}
        </div>
      )}

      {/* Filters */}
      <Card>
        <div style={{ display: "flex", gap: "var(--space-3)", alignItems: "end", flexWrap: "wrap" }}>
          <Select label="Team" value={teamFilter} onChange={setTeamFilter}
                  options={[{ value: "", label: "All teams" },
                            ...teams.map(t => ({ value: String(t.team_id), label: `${t.name}${t.company_name ? ` (${t.company_name})` : ""}` }))]} />
          <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span className="hig-caption-1">Window</span>
            <TimeRange value={range} onChange={setRange} />
          </label>
        </div>
      </Card>

      {/* Stage tiles */}
      <Card title="Pipeline">
        <div style={{ display: "grid", gridTemplateColumns: `repeat(${data.stages.length}, 1fr)`, gap: "var(--space-3)" }}>
          {data.stages.map((s, i) => {
            const pct = data.stages[0].n > 0 ? (s.n / data.stages[0].n * 100) : 0;
            return (
              <div key={s.key} style={{
                background: "var(--colour-bg-system)",
                border: "1px solid var(--colour-separator-opaque)",
                borderRadius: "var(--radius-md)",
                padding: "var(--space-4)",
              }}>
                <SectionEyebrow>{s.label}</SectionEyebrow>
                <div className="hig-large-title hig-numeric" style={{ marginTop: 4 }}>{s.n}</div>
                {i > 0 && (
                  <div className="hig-caption-1" style={{ color: "var(--colour-label-secondary)", marginTop: 4 }}>
                    {pct.toFixed(0)}% of invited
                  </div>
                )}
                <div style={{ height: 6, background: "var(--colour-fill-quaternary)", borderRadius: 999, marginTop: 8 }}>
                  <div style={{ height: "100%", width: `${(s.n / max * 100).toFixed(1)}%`,
                                background: "var(--colour-accent)", borderRadius: 999 }} />
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Invite controls (role-gated) */}
      {canSend ? (
        <Card title="Send Invites"
              action={<Button variant="filled" size="md" onClick={sendBulk}>
                {busy ? "Sending..." : "Bulk-invite unaudited reps ▸"}
              </Button>}>
          <p className="hig-callout" style={{ color: "var(--colour-label-secondary)", margin: 0 }}>
            Send a one-off invite below, or click Bulk-invite to email every unaudited
            sales rep {teamFilter ? "in the selected team" : "across all teams"}.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr 1fr auto", gap: "var(--space-2)",
                        marginTop: "var(--space-3)", alignItems: "end" }}>
            <Field label="Work email" value={email} onChange={setEmail} placeholder="rep@company.com" type="email" />
            <Field label="First name" value={first} onChange={setFirst} placeholder="First" />
            <Field label="Last name"  value={last}  onChange={setLast}  placeholder="Last" />
            <Button variant="filled" size="md" onClick={sendOne}>{busy ? "Sending..." : "Send invite ✉"}</Button>
          </div>
        </Card>
      ) : (
        <Card title="Send Invites">
          <p className="hig-callout" style={{ margin: 0 }}>
            Your role ({me ? ROLE_LABEL[me.role] : "unknown"}) is read-only on the funnel.
            Ask an Admin, Sales Director, HR or Learning &amp; Development user to send invites.
          </p>
        </Card>
      )}

      {/* Recent invites */}
      <Card title={`Recent invites (${data.recent_invites.length})`}>
        {data.recent_invites.length === 0 ? (
          <p className="hig-footnote" style={{ margin: 0 }}>No invites in this window.</p>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--type-callout)" }}>
              <thead>
                <tr>
                  {["Sent","Recipient","Email","Team","Status","Sender"].map(h => (
                    <th key={h} className="hig-caption-1"
                        style={{ textAlign: "left", textTransform: "uppercase",
                                 letterSpacing: "0.04em",
                                 color: "var(--colour-label-tertiary)",
                                 borderBottom: "1px solid var(--colour-separator)",
                                 padding: "var(--space-2)" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.recent_invites.map(inv => {
                  const name = [inv.first_name, inv.last_name].filter(Boolean).join(" ") || "-";
                  const team = teams.find(t => t.team_id === inv.team_id)?.name ?? "-";
                  const status = inv.audit_id ? "converted"
                               : inv.accepted_at ? "opened"
                               : "pending";
                  return (
                    <tr key={inv.invite_id} style={{ borderBottom: "1px solid var(--colour-separator)" }}>
                      <td style={{ padding: "var(--space-2)" }} className="hig-numeric">
                        {new Date(inv.sent_at).toLocaleDateString("en-AU")}
                      </td>
                      <td style={{ padding: "var(--space-2)" }}>{name}</td>
                      <td style={{ padding: "var(--space-2)", color: "var(--colour-label-secondary)" }}>{inv.email}</td>
                      <td style={{ padding: "var(--space-2)" }}>{team}</td>
                      <td style={{ padding: "var(--space-2)" }}>
                        <StatusPill status={status} />
                      </td>
                      <td style={{ padding: "var(--space-2)", color: "var(--colour-label-secondary)" }}>{inv.invited_by_email ?? "-"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  height: 32,
  padding: "0 var(--space-3)",
  border: "1px solid var(--colour-separator-opaque)",
  borderRadius: "var(--radius-sm)",
  background: "var(--colour-bg-system)",
  color: "var(--colour-label)",
  fontSize: "var(--type-callout)",
  fontFamily: "inherit",
};
function Field({ label, value, onChange, placeholder, type = "text" }:
  { label: string; value: string; onChange: (s: string) => void; placeholder?: string; type?: string }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span className="hig-caption-1">{label}</span>
      <input type={type} value={value} placeholder={placeholder}
             onChange={(e) => onChange(e.target.value)} style={inputStyle} />
    </label>
  );
}
function Select({ label, value, onChange, options }:
  { label: string; value: string; onChange: (s: string) => void;
    options: { value: string; label: string }[] }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 180 }}>
      <span className="hig-caption-1">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} style={inputStyle}>
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
}
function StatusPill({ status }: { status: string }) {
  const map: Record<string, string> = {
    pending:   "var(--colour-system-orange)",
    opened:    "var(--colour-system-blue)",
    converted: "var(--colour-system-green)",
  };
  return (
    <span style={{
      background: map[status] ?? "var(--colour-label-tertiary)",
      color: "#FFFFFF",
      fontSize: "var(--type-caption-1)",
      lineHeight: "var(--lead-caption-1)",
      padding: "2px 10px", borderRadius: "var(--radius-pill)", fontWeight: 600,
    }}>{status}</span>
  );
}
