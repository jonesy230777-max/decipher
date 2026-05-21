import { useEffect, useState } from "react";
import { useAuth } from "../auth";
import { api } from "../api";

type AuditRow = {
  audit_id: number;
  status: string;
  started_at: string;
  completed_at: string | null;
  archetype_name: string | null;
  report_id: number | null;
};

export default function MyProfile() {
  const { me } = useAuth();
  const [audits, setAudits] = useState<AuditRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!me) return;
    api<{ audits: AuditRow[] }>(`/api/respondents/${me.respondent_id}/audits`)
      .then((d) => setAudits(d.audits ?? []))
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [me]);

  if (!me) return null;

  const latest = audits[0] ?? null;
  const daysSinceLatest = latest?.completed_at
    ? Math.floor((Date.now() - new Date(latest.completed_at).getTime()) / 86_400_000)
    : null;
  const reauditDue = daysSinceLatest !== null && daysSinceLatest >= 90;

  return (
    <div style={{ maxWidth: 680 }}>
      <h1 className="hig-large-title" style={{ margin: "0 0 var(--space-2)" }}>
        {me.name ?? me.email}
      </h1>
      <p className="hig-callout" style={{ color: "var(--colour-label-secondary)",
                                          margin: "0 0 var(--space-6)" }}>
        {me.email}
      </p>

      {reauditDue && (
        <div role="note"
             style={{ background: "var(--colour-system-orange)", color: "#fff",
                      padding: "var(--space-3) var(--space-4)",
                      borderRadius: "var(--radius-md)",
                      marginBottom: "var(--space-5)",
                      fontSize: "var(--type-callout)", fontWeight: 600 }}>
          Your last audit was {daysSinceLatest} days ago. A re-audit keeps your profile current.
        </div>
      )}

      <h2 className="hig-title-2" style={{ margin: "0 0 var(--space-3)" }}>Your audits</h2>

      {loading && (
        <p className="hig-callout" style={{ color: "var(--colour-label-secondary)" }}>Loading...</p>
      )}
      {err && (
        <p className="hig-footnote" style={{ color: "var(--colour-system-red)" }}>{err}</p>
      )}
      {!loading && audits.length === 0 && (
        <p className="hig-callout" style={{ color: "var(--colour-label-secondary)" }}>
          No audits on record yet. You'll receive a link when your facilitator invites you.
        </p>
      )}

      {audits.map((a) => (
        <div key={a.audit_id}
             style={{ border: "1px solid var(--colour-separator-opaque)",
                      borderRadius: "var(--radius-md)",
                      padding: "var(--space-4)",
                      marginBottom: "var(--space-3)",
                      background: "var(--colour-bg-system-secondary)" }}>
          <div style={{ display: "flex", justifyContent: "space-between",
                        alignItems: "flex-start" }}>
            <div>
              <span className="hig-callout" style={{ fontWeight: 700 }}>
                Audit #{a.audit_id}
              </span>
              {a.archetype_name && (
                <span className="hig-footnote"
                      style={{ marginLeft: 8, color: "var(--colour-accent)",
                               fontWeight: 600 }}>
                  {a.archetype_name}
                </span>
              )}
            </div>
            <span className="hig-caption-1"
                  style={{ color: "var(--colour-label-tertiary)",
                           textTransform: "uppercase", letterSpacing: "0.04em" }}>
              {a.status}
            </span>
          </div>
          <div className="hig-footnote"
               style={{ color: "var(--colour-label-secondary)",
                        marginTop: "var(--space-1)" }}>
            Started {new Date(a.started_at).toLocaleDateString("en-AU")}
            {a.completed_at && ` · Completed ${new Date(a.completed_at).toLocaleDateString("en-AU")}`}
          </div>
        </div>
      ))}
    </div>
  );
}
