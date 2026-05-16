import { useEffect, useState } from "react";
import { api } from "../api";

type Event = {
  id: number;
  occurred_at: string;
  actor: string | null;
  action: string;
  severity: "info" | "warning" | "error";
  subject_id: string | null;
  payload: unknown;
};

const SEV_COLOUR: Record<Event["severity"], string> = {
  info: "var(--colour-text-secondary)",
  warning: "var(--colour-band-practising)",
  error: "var(--colour-band-developing)",
};

export default function EventsLog() {
  const [rows, setRows] = useState<Event[] | null>(null);
  useEffect(() => {
    api<{ events: Event[] }>("/api/events?limit=200").then((d) => setRows(d.events));
  }, []);
  return (
    <div>
      <h1 style={{ fontSize: "var(--type-title-1)", fontWeight: 600, margin: 0 }}>Events</h1>
      <p style={{ color: "var(--colour-text-secondary)", marginTop: "var(--space-3)" }}>
        Every state transition, agent run, and Claude call lands here. Last 200 rows.
      </p>
      {rows && rows.length === 0 ? (
        <p style={{ color: "var(--colour-text-tertiary)", marginTop: "var(--space-5)" }}>
          No events yet. Trigger one by completing an audit (M3) or running an agent.
        </p>
      ) : (
        <table style={{ marginTop: "var(--space-5)", width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ textAlign: "left", color: "var(--colour-text-secondary)", fontSize: "var(--type-subhead)" }}>
              <th style={{ padding: "var(--space-2)" }}>When</th>
              <th style={{ padding: "var(--space-2)" }}>Severity</th>
              <th style={{ padding: "var(--space-2)" }}>Actor</th>
              <th style={{ padding: "var(--space-2)" }}>Action</th>
              <th style={{ padding: "var(--space-2)" }}>Subject</th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((e) => (
              <tr key={e.id} style={{ borderTop: "1px solid var(--colour-border-subtle)" }}>
                <td style={{ padding: "var(--space-2)", fontFamily: "ui-monospace", fontSize: "var(--type-footnote)" }}>
                  {new Date(e.occurred_at).toLocaleString("en-AU")}
                </td>
                <td style={{ padding: "var(--space-2)", color: SEV_COLOUR[e.severity] }}>{e.severity}</td>
                <td style={{ padding: "var(--space-2)" }}>{e.actor ?? "-"}</td>
                <td style={{ padding: "var(--space-2)" }}>{e.action}</td>
                <td style={{ padding: "var(--space-2)", fontFamily: "ui-monospace", fontSize: "var(--type-footnote)" }}>
                  {e.subject_id ?? "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
