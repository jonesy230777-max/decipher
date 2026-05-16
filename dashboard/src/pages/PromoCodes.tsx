import { useEffect, useState } from "react";
import { api } from "../api";

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
  return (
    <div>
      <h1 style={{ fontSize: "var(--type-title-1)", fontWeight: 600, margin: 0 }}>Promo Codes</h1>
      <p style={{ color: "var(--colour-text-secondary)", marginTop: "var(--space-2)" }}>
        Free codes for comps and gifts. Discount codes for campaigns.
      </p>
      <div
        style={{
          marginTop: "var(--space-5)",
          border: "1px solid var(--colour-border-subtle)",
          borderRadius: "var(--radius-md)",
          overflow: "auto",
        }}
      >
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--type-callout)" }}>
          <thead style={{ background: "var(--colour-bg-elevated)" }}>
            <tr style={{ color: "var(--colour-text-secondary)", textAlign: "left" }}>
              <th style={{ padding: "var(--space-3)" }}>Code</th>
              <th style={{ padding: "var(--space-3)" }}>Type</th>
              <th style={{ padding: "var(--space-3)", textAlign: "right" }}>Discount</th>
              <th style={{ padding: "var(--space-3)", textAlign: "right" }}>Uses left</th>
              <th style={{ padding: "var(--space-3)" }}>Valid until</th>
              <th style={{ padding: "var(--space-3)" }}>Campaign</th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((r) => (
              <tr key={r.code} style={{ borderTop: "1px solid var(--colour-border-subtle)" }}>
                <td style={{ padding: "var(--space-3)", fontFamily: "ui-monospace", fontWeight: 600 }}>{r.code}</td>
                <td style={{ padding: "var(--space-3)", textTransform: "capitalize" }}>{r.code_type}</td>
                <td style={{ padding: "var(--space-3)", textAlign: "right", fontFamily: "ui-monospace" }}>
                  {r.discount_pct != null ? `${r.discount_pct}%` : "-"}
                </td>
                <td style={{ padding: "var(--space-3)", textAlign: "right", fontFamily: "ui-monospace" }}>
                  {r.uses_remaining ?? "∞"}
                </td>
                <td style={{ padding: "var(--space-3)", color: "var(--colour-text-tertiary)" }}>
                  {r.valid_until ? new Date(r.valid_until).toLocaleDateString("en-AU") : "no expiry"}
                </td>
                <td style={{ padding: "var(--space-3)", color: "var(--colour-text-secondary)" }}>
                  {r.source_campaign ?? "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
