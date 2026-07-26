import { useEffect, useState } from "react";
import { api } from "../api";
import { SortableTable, type Column } from "../components/SortableTable";
import { Button, Card } from "../components/Card";

type Promo = {
  code: string;
  code_type: "free" | "discount";
  discount_pct: number | null;
  uses_remaining: number | null;
  valid_until: string | null;
  source_campaign: string | null;
  created_at: string;
};

export default function PromoCodes() {
  const [rows, setRows] = useState<Promo[] | null>(null);
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [n, setN] = useState({
    code: "", code_type: "discount", discount_pct: "25",
    uses_remaining: "100", valid_until: "", source_campaign: "",
  });

  function refresh() {
    api<{ promo_codes: Promo[] }>("/api/promo-codes").then((d) => setRows(d.promo_codes));
  }
  useEffect(() => { refresh(); }, []);

    async function create() {
    if (!n.code.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api("/api/promo-codes", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: n.code.trim().toUpperCase(),
          code_type: n.code_type,
          discount_pct: n.code_type === "discount" ? Number(n.discount_pct || "0") : 100,
          uses_remaining: n.uses_remaining ? Number(n.uses_remaining) : null,
          valid_until: n.valid_until || null,
          source_campaign: n.source_campaign || null,
        }),
      });
      setAdding(false);
      setN({ code: "", code_type: "discount", discount_pct: "25",
        uses_remaining: "100", valid_until: "", source_campaign: "" });
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "unknown error");
    } finally { setBusy(false); }
    }

  const columns: Column<Promo>[] = [
    { key: "code", label: "Code", style: { fontWeight: 600, fontVariantNumeric: "tabular-nums" } },
    { key: "code_type", label: "Type", style: { textTransform: "capitalize" } },
    {
      key: "discount_pct", label: "Discount", align: "right",
      style: { fontVariantNumeric: "tabular-nums" },
      format: (r) => r.discount_pct != null ? `${r.discount_pct}%` : "·",
    },
    {
      key: "uses_remaining", label: "Uses left", align: "right",
      style: { fontVariantNumeric: "tabular-nums" },
      format: (r) => r.uses_remaining ?? "unlimited",
    },
    {
      key: "valid_until", label: "Valid until",
      style: { color: "var(--colour-label-tertiary)" },
      format: (r) => r.valid_until ? new Date(r.valid_until).toLocaleDateString("en-AU") : "no expiry",
    },
    {
      key: "source_campaign", label: "Campaign",
      style: { color: "var(--colour-label-secondary)" },
    },
  ];

  return (
    <div style={{ maxWidth: 1100, display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
      <header style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "var(--space-4)" }}>
        <div>
          <h1 className="hig-large-title" style={{ margin: 0 }}>Promo Codes</h1>
          <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-2)" }}>
            Free codes for comps and gifts. Discount codes for campaigns. Click any column heading to sort.
          </p>
        </div>
        <Button variant="filled" size="md" onClick={() => setAdding(v => !v)}>
          {adding ? "Cancel" : "Add Promo Code +"}
        </Button>
      </header>

      {adding && (
        <Card title="New Promo Code">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "var(--space-3)" }}>
            <Field label="Code" value={n.code} onChange={(v) => setN({ ...n, code: v.toUpperCase() })}
                   placeholder="LAUNCH50" />
            <SelectField label="Type" value={n.code_type} onChange={(v) => setN({ ...n, code_type: v })}
                         options={[{ value: "discount", label: "Discount" }, { value: "free", label: "Free (100%)" }]} />
            <Field label="Discount %" value={n.discount_pct} onChange={(v) => setN({ ...n, discount_pct: v })}
                   placeholder="25" type="number"
                   disabled={n.code_type === "free"} />
            <Field label="Uses remaining" value={n.uses_remaining} onChange={(v) => setN({ ...n, uses_remaining: v })}
                   placeholder="100 (blank = unlimited)" type="number" />
            <Field label="Valid until" value={n.valid_until} onChange={(v) => setN({ ...n, valid_until: v })}
                   placeholder="" type="date" />
            <Field label="Source campaign" value={n.source_campaign} onChange={(v) => setN({ ...n, source_campaign: v })}
                   placeholder="launch_campaign" />
          </div>
          {error && (
          <p className="hig-footnote" style={{ color: "#D92D20", marginTop: "var(--space-3)" }}>{error}</p>
        )}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "var(--space-2)",
                        marginTop: "var(--space-4)", paddingTop: "var(--space-4)",
                        borderTop: "1px solid var(--colour-separator)" }}>
            <Button variant="plain" size="md" onClick={() => setAdding(false)}>Cancel</Button>
            <Button variant="filled" size="md" onClick={create}>{busy ? "Saving..." : "Create Promo Code"}</Button>
          </div>
        </Card>
      )}

      <SortableTable
        rows={rows}
        columns={columns}
        rowKey={(r) => r.code}
        initialSort={{ key: "created_at", dir: "desc" }}
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
function Field({ label, value, onChange, placeholder, type = "text", disabled }:
  { label: string; value: string; onChange: (v: string) => void;
    placeholder?: string; type?: string; disabled?: boolean }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 0,
                    opacity: disabled ? 0.5 : 1 }}>
      <span className="hig-caption-1">{label}</span>
      <input type={type} value={value} placeholder={placeholder} disabled={disabled}
             onChange={(e) => onChange(e.target.value)} style={inputStyle} />
    </label>
  );
}
function SelectField({ label, value, onChange, options }:
  { label: string; value: string; onChange: (v: string) => void;
    options: { value: string; label: string }[] }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 0 }}>
      <span className="hig-caption-1">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} style={inputStyle}>
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
}
