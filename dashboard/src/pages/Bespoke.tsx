import { useEffect, useState } from "react";
import { api } from "../api";

type Bespoke = {
  bespoke_client_id: number;
  client_name: string;
  unique_url_slug: string;
  estimated_value: number | null;
  status: "draft" | "active" | "archived";
  created_at: string;
};

const STATUS_COLOUR: Record<Bespoke["status"], string> = {
  draft:    "var(--colour-label-tertiary)",
  active:   "var(--colour-system-green)",
  archived: "var(--colour-label-tertiary)",
};

export default function Bespoke() {
  const [rows, setRows] = useState<Bespoke[] | null>(null);
  useEffect(() => {
    api<{ bespoke: Bespoke[] }>("/api/bespoke").then((d) => setRows(d.bespoke));
  }, []);

  const totalPipeline = (rows ?? [])
    .filter((r) => r.status === "active")
    .reduce((acc, r) => acc + (r.estimated_value ?? 0), 0);

  return (
    <div style={{ maxWidth: 1100 }}>
      <h1 className="hig-large-title" style={{ margin: 0 }}>Bespoke clients</h1>
      <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-2)" }}>
        Custom audits and tailored engagements. Active pipeline:{" "}
        <strong className="hig-numeric">AUD ${totalPipeline.toLocaleString("en-AU")}</strong>.
      </p>

      <ul
        style={{
          marginTop: "var(--space-5)",
          listStyle: "none",
          padding: 0,
          background: "var(--colour-bg-system-secondary)",
          border: "1px solid var(--colour-separator-opaque)",
          borderRadius: "var(--radius-lg)",
          overflow: "hidden",
        }}
      >
        {rows?.map((r, i) => (
          <li
            key={r.bespoke_client_id}
            style={{
              padding: "var(--space-4) var(--space-5)",
              borderTop: i === 0 ? "none" : "1px solid var(--colour-separator)",
              display: "flex",
              alignItems: "center",
              gap: "var(--space-5)",
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="hig-headline">{r.client_name}</div>
              <div className="hig-footnote">/audit/{r.unique_url_slug}</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ color: STATUS_COLOUR[r.status], textTransform: "capitalize", fontWeight: 600 }} className="hig-callout">
                {r.status}
              </div>
              <div className="hig-numeric hig-footnote">
                {r.estimated_value ? `AUD $${r.estimated_value.toLocaleString("en-AU")}` : "·"}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
