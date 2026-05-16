import { useEffect, useState } from "react";
import { api } from "../api";

type Industry = { industry_id: number; code: string; name: string; description: string | null };

export default function Industries() {
  const [rows, setRows] = useState<Industry[] | null>(null);
  useEffect(() => {
    api<{ industries: Industry[] }>("/api/industries").then((d) => setRows(d.industries));
  }, []);
  return (
    <div>
      <h1 style={{ fontSize: "var(--type-title-1)", fontWeight: 600, margin: 0 }}>Industries</h1>
      <p style={{ color: "var(--colour-text-secondary)", marginTop: "var(--space-3)" }}>
        Vertical question banks. CRUD lands in M7.
      </p>
      <table style={{ marginTop: "var(--space-5)", width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", color: "var(--colour-text-secondary)", fontSize: "var(--type-subhead)" }}>
            <th style={{ padding: "var(--space-2)" }}>Code</th>
            <th style={{ padding: "var(--space-2)" }}>Name</th>
            <th style={{ padding: "var(--space-2)" }}>Description</th>
          </tr>
        </thead>
        <tbody>
          {rows?.map((r) => (
            <tr key={r.industry_id} style={{ borderTop: "1px solid var(--colour-border-subtle)" }}>
              <td style={{ padding: "var(--space-2)", fontFamily: "ui-monospace" }}>{r.code}</td>
              <td style={{ padding: "var(--space-2)" }}>{r.name}</td>
              <td style={{ padding: "var(--space-2)", color: "var(--colour-text-secondary)" }}>{r.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
