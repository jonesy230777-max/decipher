/**
 * Individual respondent drill-down (Owen Wright -> Grant Smith user story).
 *
 * Strict scoping is enforced server-side. This page renders identity gated
 * by `consent_share_individual` (admin always sees; others only if consent).
 */
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { Card, SectionEyebrow, Button, Separator } from "../components/Card";
import { GapAnalysis } from "../components/GapAnalysis";

type Audit = {
  audit_id: number;
  status: string;
  started_at: string;
  completed_at: string | null;
  cognitive_empathy: number | null;
  eq: number | null;
  pressure_composure: number | null;
  storytelling: number | null;
  archetype_name: string | null;
  archetype_confidence: number | null;
  report_id: number | null;
  pdf_path: string | null;
};
type Detail = {
  respondent: {
    respondent_id: number;
    email: string;
    name: string | null;
    first_name: string | null;
    last_name: string | null;
    mobile: string | null;
    job_title: string | null;
    location: string | null;
    timezone: string | null;
    company: string | null;
    industry: string | null;
    role: string;
    team_id: number | null;
    company_id: number | null;
    consent_share_individual: boolean;
    created_at: string;
  };
  team_name: string | null;
  company_name: string | null;
  company_id: number | null;
  audits: Audit[];
  bands_by_dim: Record<string, { dimension: string; band: string; score: number }>;
  identity_visible: boolean;
};

const DIM_LABEL: Record<string, string> = {
  cognitive_empathy:  "Cognitive Empathy",
  eq:                 "Emotional Intelligence",
  pressure_composure: "Pressure Composure",
  storytelling:       "Storytelling",
};

export default function RespondentDetail() {
  const { id } = useParams();
  const [data, setData] = useState<Detail | null>(null);
  const [err,  setErr]  = useState<string | null>(null);

  useEffect(() => {
    api<Detail>(`/api/respondents/${id}`).then(setData).catch((e) => setErr(String(e)));
  }, [id]);

  if (err)  return <p className="hig-footnote" style={{ color: "var(--colour-system-red)" }}>{err}</p>;
  if (!data) return <p className="hig-footnote">Loading respondent...</p>;

  const r = data.respondent;
  const latest = data.audits[0];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)", maxWidth: 1100 }}>
      {/* Breadcrumb */}
      <div className="hig-footnote">
        {data.company_id && data.company_name && (
          <>
            <Link to="/companies" style={{ color: "var(--colour-accent)" }}>Companies</Link>
            {" · "}
            <Link to={`/companies/${r.company_id}`} style={{ color: "var(--colour-accent)" }}>
              {data.company_name}
            </Link>
            {" · "}
          </>
        )}
        {data.team_name && r.team_id && (
          <>
            <Link to={`/teams/${r.team_id}`} style={{ color: "var(--colour-accent)" }}>
              {data.team_name}
            </Link>
            {" · "}
          </>
        )}
        <span>Respondent</span>
      </div>

      {/* Identity header */}
      <header style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "var(--space-5)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)" }}>
          <span
            aria-hidden="true"
            style={{
              width: 56, height: 56, borderRadius: "50%",
              background: "var(--colour-accent)", color: "#FFFFFF",
              display: "inline-flex", alignItems: "center", justifyContent: "center",
              fontWeight: 700, fontSize: 22,
            }}
          >
            {(r.name ?? "?").slice(0, 1).toUpperCase()}
          </span>
          <div>
            <h1 className="hig-large-title" style={{ margin: 0 }}>{r.name ?? "Anonymised"}</h1>
            <p className="hig-subhead" style={{ margin: "var(--space-1) 0 0 0" }}>
              {data.identity_visible ? r.email : "anonymised · consent not granted"}
              {" · "}{r.role.replace("_", " ")}
            </p>
          </div>
        </div>
        <div style={{ display: "flex", gap: "var(--space-2)" }}>
          <InviteButton respondent={r} />
          {latest && <RescoreButton auditId={latest.audit_id} onDone={() => location.reload()} />}
          {latest?.report_id && (
            <Button href={`/api/reports/${latest.report_id}/download`} variant="filled" size="md">
              Download report ↓
            </Button>
          )}
        </div>
      </header>

      {/* Contact card */}
      <Card title="Contact Details">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "var(--space-4)" }}>
          <KV label="First name" value={r.first_name ?? "·"} />
          <KV label="Last name"  value={r.last_name ?? "·"} />
          <KV label="Job title"  value={r.job_title ?? "·"} />
          <KV label="Email"      value={data.identity_visible ? r.email : "anonymised"} />
          <KV label="Mobile"     value={data.identity_visible ? (r.mobile ?? "·") : "anonymised"} />
          <KV label="Timezone"   value={r.timezone ?? "Australia/Sydney"} />
          <KV label="Team"       value={data.team_name ?? "·"} />
          <KV label="Company"    value={data.company_name ?? "·"} />
          <KV label="Industry"   value={r.industry ?? "·"} />
        </div>
      </Card>

      {/* Consent banner */}
      {!data.identity_visible && (
        <Card>
          <SectionEyebrow>Consent</SectionEyebrow>
          <p className="hig-callout" style={{ margin: 0, color: "var(--colour-label-secondary)" }}>
            This respondent has not consented to share individual identity with team
            leaders. Their scores, archetype and band remain visible. Name and email
            are hidden until consent is granted, or for admin viewers.
          </p>
        </Card>
      )}

      {/* Latest scores */}
      {latest && (
        <Card title={`Latest audit · ${new Date(latest.started_at).toLocaleDateString("en-AU")}`}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "var(--space-4)" }}>
            {(["cognitive_empathy","eq","pressure_composure","storytelling"] as const).map((k) => {
              const s = latest[k];
              const band = data.bands_by_dim[k]?.band ?? "-";
              return (
                <div key={k} style={{
                  background: "var(--colour-bg-system)",
                  border: "1px solid var(--colour-separator-opaque)",
                  borderRadius: "var(--radius-md)",
                  padding: "var(--space-4)",
                }}>
                  <div className="hig-caption-1">{DIM_LABEL[k]}</div>
                  <div className="hig-large-title hig-numeric" style={{ marginTop: 4 }}>
                    {s != null ? (s * 100).toFixed(1) : "-"}
                  </div>
                  <div style={{ marginTop: "var(--space-2)" }}>
                    <BandPill band={band} />
                  </div>
                </div>
              );
            })}
          </div>

          <Separator />

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "var(--space-4)" }}>
            <KV label="Archetype" value={latest.archetype_name ?? "-"} />
            <KV label="Confidence" value={latest.archetype_confidence != null ? `${(latest.archetype_confidence * 100).toFixed(1)}%` : "-"} />
            <KV label="Status" value={latest.status} />
          </div>
        </Card>
      )}

      {/* Gap analysis (individual vs team + cohort) */}
      <GapAnalysis kind="individual" href={`/api/respondents/${id}/gap-analysis`} />

      {/* Audit history */}
      {data.audits.length > 1 && (
        <Card title="Audit History">
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {data.audits.map((a, i) => (
              <li
                key={a.audit_id}
                style={{
                  padding: "var(--space-3) 0",
                  borderTop: i === 0 ? "none" : "1px solid var(--colour-separator)",
                  display: "flex", alignItems: "center", gap: "var(--space-4)",
                }}
              >
                <div className="hig-footnote hig-numeric" style={{ width: 120 }}>
                  {new Date(a.started_at).toLocaleDateString("en-AU")}
                </div>
                <div className="hig-callout" style={{ flex: 1 }}>
                  {a.archetype_name ?? "-"} · status: {a.status}
                </div>
                <div className="hig-callout hig-numeric" style={{ color: "var(--colour-label-secondary)" }}>
                  CE {fmt(a.cognitive_empathy)} · EQ {fmt(a.eq)} · PC {fmt(a.pressure_composure)} · ST {fmt(a.storytelling)}
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <footer className="hig-footnote" style={{ textAlign: "center", padding: "var(--space-5) 0", borderTop: "1px solid var(--colour-separator-opaque)" }}>
        decipher.com.au · Individual report scoped to {data.team_name ?? "no team"} · Identity gated by respondent consent
      </footer>
    </div>
  );
}

function RescoreButton({ auditId, onDone }: { auditId: number; onDone: () => void }) {
  const { me } = useAuth();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg]   = useState<string | null>(null);
  if (me?.role !== "admin") return null;
  async function run() {
    if (!confirm(`Re-score audit #${auditId} and regenerate the PDF report?`)) return;
    setBusy(true);
    try {
        const json = await api<{ archetype: string; report?: { version: number } }>(`/api/audit/${auditId}/score`, { method: "POST" });
        setMsg(`Re-scored: ${json.archetype} (report v${json.report?.version}).`);
        setTimeout(() => { setMsg(null); onDone(); }, 1200);
    } catch (e) {
        setMsg(`Failed: ${e instanceof Error ? e.message : "unknown error"}`);
        setTimeout(() => setMsg(null), 5000);
    } finally { setBusy(false); }
  }
  return (
    <>
      <Button variant="plain" size="md" onClick={run}>
        {busy ? "Re-scoring..." : "Re-score ↻"}
      </Button>
      {msg && (
        <div className="hig-caption-1"
             style={{ position: "fixed", bottom: 24, right: 24, zIndex: 80,
                      background: "var(--colour-bg-system-secondary)",
                      border: "1px solid var(--colour-separator-opaque)",
                      borderRadius: 8, padding: 12, boxShadow: "var(--shadow-2)",
                      maxWidth: 360 }}>
          {msg}
        </div>
      )}
    </>
  );
}

function InviteButton({ respondent }: { respondent: Detail["respondent"] }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg]   = useState<string | null>(null);
  async function send() {
    if (!confirm(`Send a Decipher DNA audit invite to ${respondent.email}?`)) return;
    setBusy(true);
    try {
        const json = await api<{ delivered: boolean; link?: string; error?: string }>("/api/audit/invite", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: respondent.email,
          first_name: respondent.first_name,
          last_name: respondent.last_name,
          mobile: respondent.mobile,
          team_id: respondent.team_id,
          company_id: respondent.company_id,
        }),
      });
      setMsg(json.delivered
        ? `Invite delivered to Mailpit. Link: ${json.link}`
        : `Recorded but SMTP failed: ${json.error ?? "unknown"}`);
      setTimeout(() => setMsg(null), 6000);
    } catch (e) {
        setMsg(`Failed: ${e instanceof Error ? e.message : "unknown error"}`);
        setTimeout(() => setMsg(null), 6000);
    } finally { setBusy(false); }
  }
  return (
    <>
      <Button variant="tinted" size="md" onClick={send}>
        {busy ? "Sending..." : "Send audit invite ✉"}
      </Button>
      {msg && (
        <div className="hig-caption-1"
             style={{ position: "fixed", bottom: 24, right: 24, zIndex: 80,
                      background: "var(--colour-bg-system-secondary)",
                      border: "1px solid var(--colour-separator-opaque)",
                      borderRadius: 8, padding: 12, boxShadow: "var(--shadow-2)",
                      maxWidth: 360 }}>
          {msg}
        </div>
      )}
    </>
  );
}

function fmt(v: number | null): string {
  return v != null ? (v * 100).toFixed(0) : "-";
}

function KV({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="hig-caption-1">{label}</div>
      <div className="hig-headline" style={{ marginTop: 2 }}>{value}</div>
    </div>
  );
}

function BandPill({ band }: { band: string }) {
  const map: Record<string, string> = {
    elite:      "var(--colour-band-elite)",
    performing: "var(--colour-band-performing)",
    practising: "var(--colour-band-practising)",
    developing: "var(--colour-band-developing)",
  };
  const label = band.charAt(0).toUpperCase() + band.slice(1);
  return (
    <span
      style={{
        background: map[band] ?? "var(--colour-label-tertiary)",
        color: "#FFFFFF",
        fontSize: "var(--type-caption-1)",
        lineHeight: "var(--lead-caption-1)",
        padding: "2px 10px",
        borderRadius: "var(--radius-pill)",
        fontWeight: 600,
      }}
    >
      {label}
    </span>
  );
}
