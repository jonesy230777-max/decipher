import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { SortableTable, type Column } from "../components/SortableTable";
import { Card, Button } from "../components/Card";

type Industry = { industry_id: number; code: string; name: string; description: string | null };

export default function Industries() {
  const { me } = useAuth();
  const isAdmin = me?.role === "admin";
  const [rows, setRows] = useState<Industry[] | null>(null);
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState(false);
  const [n, setN] = useState({ code: "", name: "", description: "" });

  function refresh() {
    api<{ industries: Industry[] }>("/api/industries").then((d) => setRows(d.industries));
  }
  useEffect(() => { refresh(); }, []);

  async function create() {
    if (!n.code.trim() || !n.name.trim()) return;
    setBusy(true);
    try {
      await api("/api/industries", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        code: n.code.trim().toLowerCase(),
        name: n.name.trim(),
        description: n.description.trim() || null,
      }),
      });
    setAdding(false);
    setN({ code: "", name: "", description: "" });
    refresh();
    } finally { setBusy(false); }
  }

  const columns: Column<Industry>[] = [
    { key: "code", label: "Code", style: { fontVariantNumeric: "tabular-nums", fontWeight: 600 } },
    { key: "name", label: "Name" },
    { key: "description", label: "Description",
      format: (r) => <span style={{ color: "var(--colour-label-secondary)" }}>{r.description}</span> },
  ];

  return (
    <div style={{ maxWidth: 1100, display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
      <header style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "var(--space-4)" }}>
        <div>
          <h1 className="hig-large-title" style={{ margin: 0 }}>Industries</h1>
          <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-2)" }}>
            Vertical question banks. Click any column heading to sort.
          </p>
        </div>
        {isAdmin && (
          <Button variant="filled" size="md" onClick={() => setAdding(v => !v)}>
            {adding ? "Cancel" : "Add Industry +"}
          </Button>
        )}
      </header>

      {adding && (
        <Card title="New Industry">
          <div style={{ display: "grid",
                        gridTemplateColumns: "0.6fr 1fr 2fr",
                        gap: "var(--space-3)" }}>
            <Field label="Code" value={n.code} onChange={(v) => setN({ ...n, code: v.toLowerCase() })}
                   placeholder="health" />
            <Field label="Name" value={n.name} onChange={(v) => setN({ ...n, name: v })}
                   placeholder="Healthcare" />
            <Field label="Description" value={n.description} onChange={(v) => setN({ ...n, description: v })}
                   placeholder="What's in the question bank" />
          </div>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "var(--space-2)",
                        marginTop: "var(--space-4)", paddingTop: "var(--space-4)",
                        borderTop: "1px solid var(--colour-separator)" }}>
            <Button variant="plain" size="md" onClick={() => setAdding(false)}>Cancel</Button>
            <Button variant="filled" size="md" onClick={create}>{busy ? "Saving..." : "Create Industry"}</Button>
          </div>
        </Card>
      )}

      <SortableTable
        rows={rows}
        columns={columns}
        rowKey={(r) => r.industry_id}
        initialSort={{ key: "code", dir: "asc" }}
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
function Field({ label, value, onChange, placeholder }:
  { label: string; value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 0 }}>
      <span className="hig-caption-1">{label}</span>
      <input value={value} placeholder={placeholder}
             onChange={(e) => onChange(e.target.value)} style={inputStyle} />
    </label>
  );
}
