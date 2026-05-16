import { useEffect, useState } from "react";
import { api } from "../api";
import { SortableTable, type Column } from "../components/SortableTable";

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
  info:    "var(--colour-label-secondary)",
  warning: "var(--colour-system-orange)",
  error:   "var(--colour-system-red)",
};

export default function EventsLog() {
  const [rows, setRows] = useState<Event[] | null>(null);
  useEffect(() => {
    api<{ events: Event[] }>("/api/events?limit=200").then((d) => setRows(d.events));
  }, []);

  const columns: Column<Event>[] = [
    {
      key: "occurred_at", label: "When",
      style: { fontVariantNumeric: "tabular-nums" },
      format: (e) => (
        <span className="hig-footnote">{new Date(e.occurred_at).toLocaleString("en-AU")}</span>
      ),
    },
    {
      key: "severity", label: "Severity",
      format: (e) => (
        <span style={{ color: SEV_COLOUR[e.severity], fontWeight: 600 }}>{e.severity}</span>
      ),
    },
    { key: "actor",      label: "Actor" },
    { key: "action",     label: "Action" },
    {
      key: "subject_id", label: "Subject",
      style: { fontVariantNumeric: "tabular-nums" },
      format: (e) => <span className="hig-footnote">{e.subject_id ?? "·"}</span>,
    },
  ];

  return (
    <div>
      <h1 className="hig-large-title" style={{ margin: 0 }}>Events</h1>
      <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-2)" }}>
        Every state transition, agent run, and Claude call lands here. Last 200 rows. Click any column heading to sort.
      </p>
      <div style={{ marginTop: "var(--space-5)" }}>
        <SortableTable
          rows={rows}
          columns={columns}
          rowKey={(e) => e.id}
          initialSort={{ key: "occurred_at", dir: "desc" }}
          empty="No events yet. Trigger one by completing an audit (M3) or running an agent."
        />
      </div>
    </div>
  );
}
