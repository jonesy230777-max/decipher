import { useEffect, useState } from "react";
import { api } from "../api";
import { Card, SectionEyebrow, Button } from "../components/Card";

type Export = {
  export_id: number;
  generated_at: string;
  bundle_path: string;
  file_count: number;
  size_bytes: number;
  summary: string;
  cost_usd: number;
};
type ExportList = { exports: Export[]; file_tree: string[] };

export default function SquarespaceExport() {
  const [data, setData] = useState<ExportList | null>(null);
  const [selected, setSelected] = useState<number | null>(null);

  useEffect(() => {
    api<ExportList>("/api/squarespace/exports").then((d) => {
      setData(d);
      if (d.exports.length > 0) setSelected(d.exports[0].export_id);
    });
  }, []);

  const current = data?.exports.find((e) => e.export_id === selected) ?? null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
      <header style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "var(--space-4)" }}>
        <div>
          <h1 style={{ fontSize: "var(--type-title-1)", fontWeight: 600, margin: 0 }}>Squarespace Export</h1>
          <p style={{ color: "var(--colour-text-secondary)", marginTop: "var(--space-2)", maxWidth: 640 }}>
            Generate, preview, and download the asset bundle Steve uploads to Squarespace.
            This page is the contract between the local prototype and the public site.
          </p>
        </div>
        <Button variant="filled" onClick={() => alert("Generation pipeline lands in M10.")}>
          Generate New Export →
        </Button>
      </header>

      {current && (
        <Card>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <SectionEyebrow>Most recent bundle</SectionEyebrow>
              <div style={{ fontSize: "var(--type-title-3)", fontWeight: 600, marginTop: "var(--space-1)" }}>
                {current.summary}
              </div>
              <div style={{ color: "var(--colour-text-tertiary)", fontSize: "var(--type-footnote)", marginTop: "var(--space-2)" }}>
                {new Date(current.generated_at).toLocaleString("en-AU")} ·{" "}
                {current.file_count} files · {(current.size_bytes / 1024).toFixed(1)} KB ·{" "}
                cost USD ${current.cost_usd.toFixed(4)}
              </div>
            </div>
          </div>
        </Card>
      )}

      <section style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "var(--space-5)" }}>
        <Card title="Preview tree">
          <ul
            style={{
              listStyle: "none",
              padding: 0,
              margin: 0,
              fontFamily: "ui-monospace",
              fontSize: "var(--type-footnote)",
              color: "var(--colour-text-secondary)",
              maxHeight: 360,
              overflowY: "auto",
            }}
          >
            {data?.file_tree.map((p) => (
              <li
                key={p}
                style={{
                  padding: "2px 0",
                  paddingLeft: `${(p.split("/").length - 1) * 16}px`,
                }}
              >
                {p}
              </li>
            ))}
          </ul>
        </Card>

        <Card title="History">
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {data?.exports.map((e) => (
              <li
                key={e.export_id}
                style={{
                  padding: "var(--space-3) 0",
                  borderTop: "1px solid var(--colour-border-subtle)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "var(--space-3)",
                  cursor: "pointer",
                }}
                onClick={() => setSelected(e.export_id)}
              >
                <div>
                  <div style={{ fontWeight: selected === e.export_id ? 700 : 500 }}>
                    v{e.export_id}
                  </div>
                  <div style={{ color: "var(--colour-text-tertiary)", fontSize: "var(--type-footnote)" }}>
                    {new Date(e.generated_at).toLocaleDateString("en-AU")}
                  </div>
                </div>
                <a
                  href={`/api/squarespace/exports/${e.export_id}/download`}
                  download
                  style={{
                    fontSize: "var(--type-footnote)",
                    color: "var(--colour-accent)",
                    fontWeight: 600,
                  }}
                  onClick={(ev) => ev.stopPropagation()}
                >
                  re-download
                </a>
              </li>
            ))}
          </ul>
        </Card>
      </section>

      {/* The single most important UI element on the page (spec §7D). */}
      <div
        data-testid="download-bundle-strip"
        style={{
          display: "flex",
          justifyContent: "flex-end",
          padding: "var(--space-4) 0",
          borderTop: "1px solid var(--colour-border-subtle)",
        }}
      >
        {current && (
          <Button
            href={`/api/squarespace/exports/${current.export_id}/download`}
            download
            variant="filled"
          >
            Download Bundle (.zip) ↓
          </Button>
        )}
      </div>
    </div>
  );
}
