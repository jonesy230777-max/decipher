import { useEffect, useState } from "react";
import { api } from "../api";
import { SortableTable, type Column } from "../components/SortableTable";

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
  in_progress: "var(--colour-label-tertiary)",
  completed:   "var(--colour-system-blue)",
  scored:      "var(--colour-system-blue)",
  reported:    "var(--colour-system-green)",
  failed_quality_gate: "var(--colour-system-red)",
};

const fmtPct = (v: number | null) =>
  v === null || v === undefined ? "·" : `${(v * 100).toFixed(0)}`;

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

  const columns: Column<Audit>[] = [
    {
      key: "audit_id", label: "ID",
      style: { fontVariantNumeric: "tabular-nums" },
    },
    {
      key: "respondent_name", label: "Respondent",
      sortValue: (a) => (a.respondent_name ?? a.email ?? "").toLowerCase(),
      format: (a) => (
        <>
          <div>{a.respondent_name ?? a.email}</div>
          <div className="hig-caption-1">{a.email}</div>
        </>
      ),
    },
    { key: "industry", label: "Industry" },
    {
      key: "status", label: "Status",
      format: (a) => (
        <span style={{ color: STATUS_COLOUR[a.status] }}>
          {a.status.replace("_", " ")}
        </span>
      ),
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
    <div>
      <h1 className="hig-large-title" style={{ margin: 0 }}>Audits</h1>
      <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-2)" }}>
        Every audit across every client. <span className="hig-numeric">{rows?.length ?? "..."}</span> rows shown. Click any column heading to sort.
      </p>

      <div
        role="tablist"
        style={{
          display: "inline-flex",
          gap: 2,
          background: "var(--colour-fill-tertiary)",
          padding: 2,
          borderRadius: "var(--radius-sm)",
          marginTop: "var(--space-4)",
          marginBottom: "var(--space-4)",
        }}
      >
        {(["all", "reported", "scored", "completed", "in_progress"] as const).map((f) => {
          const active = filter === f;
          return (
            <button
              key={f}
              role="tab"
              aria-selected={active}
              onClick={() => setFilter(f)}
              className="hig-footnote"
              style={{
                padding: "6px 10px",
                borderRadius: 4,
                border: "none",
                background: active ? "var(--colour-bg-system)" : "transparent",
                color: "var(--colour-label)",
                fontWeight: active ? 600 : 400,
                cursor: "pointer",
                boxShadow: active ? "var(--shadow-1)" : "none",
              }}
            >
              {f.replace("_", " ")}
              {f !== "all" && counts[f] !== undefined ? ` (${counts[f]})` : ""}
            </button>
          );
        })}
      </div>

      <SortableTable
        rows={rows}
        columns={columns}
        rowKey={(a) => a.audit_id}
        initialSort={{ key: "started_at", dir: "desc" }}
      />
    </div>
  );
}
