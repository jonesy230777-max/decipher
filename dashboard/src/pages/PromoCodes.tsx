import { useEffect, useState } from "react";
import { api } from "../api";
import { SortableTable, type Column } from "../components/SortableTable";

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
  useEffect(() => {
    api<{ promo_codes: Promo[] }>("/api/promo-codes").then((d) => setRows(d.promo_codes));
  }, []);

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
    <div style={{ maxWidth: 1100 }}>
      <h1 className="hig-large-title" style={{ margin: 0 }}>Promo Codes</h1>
      <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-2)" }}>
        Free codes for comps and gifts. Discount codes for campaigns. Click any column heading to sort.
      </p>
      <div style={{ marginTop: "var(--space-5)" }}>
        <SortableTable
          rows={rows}
          columns={columns}
          rowKey={(r) => r.code}
          initialSort={{ key: "created_at", dir: "desc" }}
        />
      </div>
    </div>
  );
}
