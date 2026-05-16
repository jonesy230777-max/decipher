import { useEffect, useState } from "react";
import { api } from "../api";
import { SortableTable, type Column } from "../components/SortableTable";

type Industry = { industry_id: number; code: string; name: string; description: string | null };

export default function Industries() {
  const [rows, setRows] = useState<Industry[] | null>(null);
  useEffect(() => {
    api<{ industries: Industry[] }>("/api/industries").then((d) => setRows(d.industries));
  }, []);
  const columns: Column<Industry>[] = [
    { key: "code", label: "Code", style: { fontVariantNumeric: "tabular-nums" } },
    { key: "name", label: "Name" },
    { key: "description", label: "Description",
      format: (r) => <span style={{ color: "var(--colour-label-secondary)" }}>{r.description}</span> },
  ];
  return (
    <div style={{ maxWidth: 1100 }}>
      <h1 className="hig-large-title" style={{ margin: 0 }}>Industries</h1>
      <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-2)" }}>
        Vertical question banks. CRUD lands in M7. Click any column heading to sort.
      </p>
      <div style={{ marginTop: "var(--space-5)" }}>
        <SortableTable
          rows={rows}
          columns={columns}
          rowKey={(r) => r.industry_id}
          initialSort={{ key: "code", dir: "asc" }}
        />
      </div>
    </div>
  );
}
