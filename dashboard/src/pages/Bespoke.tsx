import { useEffect, useState } from "react";
import { api } from "../api";
import { Card } from "../components/Card";

type Bespoke = {
  bespoke_client_id: number;
  client_name: string;
  unique_url_slug: string;
  estimated_value: number | null;
  status: "draft" | "active" | "archived";
  created_at: string;
};

const STATUS_COLOUR: Record<Bespoke["status"], string> = {
  draft: "var(--colour-text-tertiary)",
  active: "var(--colour-band-elite)",
  archived: "var(--colour-band-developing)",
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
    <div>
      <h1 style={{ fontSize: "var(--type-title-1)", fontWeight: 600, margin: 0 }}>Bespoke clients</h1>
      <p style={{ color: "var(--colour-text-secondary)", marginTop: "var(--space-2)" }}>
        Custom audits and tailored engagements. Active pipeline:{" "}
        <strong>AUD ${totalPipeline.toLocaleString("en-AU")}</strong>.
      </p>
      <div style={{ marginTop: "var(--space-5)", display: "grid", gap: "var(--space-3)" }}>
        {rows?.map((r) => (
          <Card key={r.bespoke_client_id}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "var(--space-4)" }}>
              <div>
                <div style={{ fontSize: "var(--type-title-3)", fontWeight: 600 }}>{r.client_name}</div>
                <div style={{ color: "var(--colour-text-tertiary)", fontFamily: "ui-monospace", fontSize: "var(--type-footnote)", marginTop: "var(--space-1)" }}>
                  /audit/{r.unique_url_slug}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ color: STATUS_COLOUR[r.status], textTransform: "capitalize", fontWeight: 600 }}>
                  {r.status}
                </div>
                <div style={{ fontFamily: "ui-monospace", marginTop: "var(--space-1)" }}>
                  {r.estimated_value
                    ? `AUD $${r.estimated_value.toLocaleString("en-AU")}`
                    : "-"}
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
