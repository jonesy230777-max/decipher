import { useEffect, useState } from "react";
import { api } from "../api";

type Audit = {
  audit_id: number;
  status: "in_progress" | "completed" | "scored" | "reported" | "failed_quality_gate";
  started_at: string;
  completed_at: string | null;
  email: string;
  respondent_name: string | null;
  company: string | null;
  industry: string | null;
  cognitive_empathy: number | null;
  eq: number | null;
  pressure_composure: number | null;
  storytelling: number | null;
  archetype_code: string | null;
  archetype_name: string | null;
  archetype_confidence: number | null;
  report_id: number | null;
};

const STATUS_COLOUR: Record<Audit["status"], string> = {
  in_progress: "var(--colour-text-tertiary)",
  completed: "var(--colour-band-performing)",
  scored: "var(--colour-band-performing)",
  reported: "var(--colour-band-elite)",
  failed_quality_gate: "var(--colour-band-developing)",
};

function fmtPct(v: number | null) {
  return v === null || v === undefined ? "-" : `${(v * 100).toFixed(0)}`;
}

export default function Audits() {
  const [rows, setRows] = useState<Audit[] | null>(null);
  const [filter, setFilter] = useState<string>("all");
  useEffect(() => {
    const q = filter === "all" ? "" : `?status=${filter}`;
    api<{ audits: Audit[] }>(`/api/audits${q}`).then((d) => setRows(d.audits));
  }, [filter]);

  const counts = rows
    ? rows.reduce<Record<string, number>>((acc, a) => {
        acc[a.status] = (acc[a.status] ?? 0) + 1;
        return acc;
      }, {})
    : {};

  return (
    <div>
      <h1 style={{ fontSize: "var(--type-title-1)", fontWeight: 600, margin: 0 }}>Audits</h1>
      <p style={{ color: "var(--colour-text-secondary)", marginTop: "var(--space-2)" }}>
        Every audit across every client. {rows?.length ?? "…"} rows shown.
      </p>

      <div style={{ display: "flex", gap: "var(--space-2)", margin: "var(--space-4) 0" }}>
        {(["all", "reported", "scored", "completed", "in_progress"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: "var(--space-2) var(--space-3)",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--colour-border-subtle)",
              background:
                filter === f ? "var(--colour-fill-primary)" : "var(--colour-bg-elevated)",
              color:
                filter === f ? "var(--colour-bg-base)" : "var(--colour-text-primary)",
              fontSize: "var(--type-footnote)",
              cursor: "pointer",
            }}
          >
            {f.replace("_", " ")}
            {f !== "all" && counts[f] !== undefined ? ` (${counts[f]})` : ""}
          </button>
        ))}
      </div>

      <div
        style={{
          border: "1px solid var(--colour-border-subtle)",
          borderRadius: "var(--radius-md)",
          overflow: "auto",
        }}
      >
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--type-footnote)" }}>
          <thead style={{ background: "var(--colour-bg-elevated)" }}>
            <tr style={{ textAlign: "left", color: "var(--colour-text-secondary)" }}>
              <th style={{ padding: "var(--space-3)" }}>ID</th>
              <th style={{ padding: "var(--space-3)" }}>Respondent</th>
              <th style={{ padding: "var(--space-3)" }}>Industry</th>
              <th style={{ padding: "var(--space-3)" }}>Status</th>
              <th style={{ padding: "var(--space-3)", textAlign: "right" }}>CE</th>
              <th style={{ padding: "var(--space-3)", textAlign: "right" }}>EQ</th>
              <th style={{ padding: "var(--space-3)", textAlign: "right" }}>PC</th>
              <th style={{ padding: "var(--space-3)", textAlign: "right" }}>ST</th>
              <th style={{ padding: "var(--space-3)" }}>Archetype</th>
              <th style={{ padding: "var(--space-3)" }}>Started</th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((a) => (
              <tr key={a.audit_id} style={{ borderTop: "1px solid var(--colour-border-subtle)" }}>
                <td style={{ padding: "var(--space-3)", fontFamily: "ui-monospace" }}>{a.audit_id}</td>
                <td style={{ padding: "var(--space-3)" }}>
                  <div>{a.respondent_name ?? a.email}</div>
                  <div style={{ color: "var(--colour-text-tertiary)" }}>{a.email}</div>
                </td>
                <td style={{ padding: "var(--space-3)" }}>{a.industry ?? "-"}</td>
                <td style={{ padding: "var(--space-3)", color: STATUS_COLOUR[a.status] }}>
                  {a.status.replace("_", " ")}
                </td>
                <td style={{ padding: "var(--space-3)", textAlign: "right", fontFamily: "ui-monospace" }}>
                  {fmtPct(a.cognitive_empathy)}
                </td>
                <td style={{ padding: "var(--space-3)", textAlign: "right", fontFamily: "ui-monospace" }}>
                  {fmtPct(a.eq)}
                </td>
                <td style={{ padding: "var(--space-3)", textAlign: "right", fontFamily: "ui-monospace" }}>
                  {fmtPct(a.pressure_composure)}
                </td>
                <td style={{ padding: "var(--space-3)", textAlign: "right", fontFamily: "ui-monospace" }}>
                  {fmtPct(a.storytelling)}
                </td>
                <td style={{ padding: "var(--space-3)" }}>{a.archetype_name ?? "-"}</td>
                <td style={{ padding: "var(--space-3)", color: "var(--colour-text-tertiary)" }}>
                  {new Date(a.started_at).toLocaleDateString("en-AU")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
