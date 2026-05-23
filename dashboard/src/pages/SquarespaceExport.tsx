import { useEffect, useRef, useState } from "react";
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

// Group file tree paths by top-level directory for rendering
function groupTree(paths: string[]): Record<string, string[]> {
  const groups: Record<string, string[]> = {};
  for (const p of paths) {
    const parts = p.split("/");
    const top = parts.length > 1 ? parts[0] : "(root)";
    (groups[top] ??= []).push(p);
  }
  return groups;
}

function fileIcon(path: string) {
  if (path.endsWith(".json")) return "{ }";
  if (path.endsWith(".md")) return "§";
  return "·";
}

export default function SquarespaceExport() {
  const [data, setData]               = useState<ExportList | null>(null);
  const [selected, setSelected]       = useState<number | null>(null);
  const [busy, setBusy]               = useState(false);
  const [flash, setFlash]             = useState<{ msg: string; ok: boolean } | null>(null);
  const [previewPath, setPreviewPath] = useState<string | null>(null);
  const [previewContent, setPreviewContent] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const dialogRef = useRef<HTMLDialogElement>(null);

  function refresh() {
    return api<ExportList>("/api/squarespace/exports").then((d) => {
      setData(d);
      if (d.exports.length > 0) setSelected(d.exports[0].export_id);
    });
  }

  useEffect(() => { refresh(); }, []);

  // Open native dialog on previewPath change
  useEffect(() => {
    if (previewPath) {
      dialogRef.current?.showModal();
    } else {
      dialogRef.current?.close();
      setPreviewContent(null);
    }
  }, [previewPath]);

  async function generate() {
    setBusy(true);
    setFlash(null);
    try {
      const r = await fetch("/api/squarespace/generate", { method: "POST" });
      const json = await r.json();
      if (!r.ok) throw new Error(json.detail ?? String(r.status));
      await refresh();
      setSelected(json.export_id);
      setFlash({
        msg: `Export #${json.export_id} generated -- ${json.file_count} files, AUD/USD ${json.cost_usd?.toFixed(4) ?? "n/a"} Claude cost.`,
        ok: true,
      });
      setTimeout(() => setFlash(null), 6000);
    } catch (e) {
      setFlash({ msg: `Failed: ${String(e)}`, ok: false });
    } finally {
      setBusy(false);
    }
  }

  async function openPreview(path: string) {
    if (!selected) return;
    setPreviewPath(path);
    setPreviewContent(null);
    setPreviewLoading(true);
    try {
      const resp = await fetch(`/api/squarespace/exports/${selected}/files/${path}`);
      if (!resp.ok) {
        setPreviewContent(`Error ${resp.status}: ${await resp.text()}`);
      } else {
        setPreviewContent(await resp.text());
      }
    } catch (e) {
      setPreviewContent(`Network error: ${String(e)}`);
    } finally {
      setPreviewLoading(false);
    }
  }

  function closePreview() {
    setPreviewPath(null);
  }

  const current = data?.exports.find((e) => e.export_id === selected) ?? null;
  const groups  = data ? groupTree(data.file_tree) : {};
  const hasBundle = current && current.file_count > 0 && current.bundle_path;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)", maxWidth: 1400 }}>
      <header style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "var(--space-5)" }}>
        <div>
          <h1 className="hig-large-title" style={{ margin: 0 }}>Squarespace Export</h1>
          <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-2)", maxWidth: 640 }}>
            Generate the asset bundle Steve uploads to Squarespace. Claude Haiku writes all page copy
            from the live brand voice. Takes 20-30 seconds.
          </p>
        </div>
        <Button variant="tinted" size="lg" onClick={generate} disabled={busy}>
          {busy ? "Generating... (20-30 s)" : "Generate New Export"}
        </Button>
      </header>

      {flash && (
        <div
          role="status"
          className="hig-callout"
          style={{
            padding: "var(--space-3) var(--space-4)",
            background: flash.ok
              ? "color-mix(in srgb, var(--colour-system-green) 10%, transparent)"
              : "color-mix(in srgb, var(--colour-system-red) 10%, transparent)",
            color: flash.ok ? "var(--colour-system-green)" : "var(--colour-system-red)",
            border: `1px solid ${flash.ok ? "var(--colour-system-green)" : "var(--colour-system-red)"}`,
            borderRadius: "var(--radius-md)",
          }}
        >
          {flash.msg}
        </div>
      )}

      {current && (
        <Card>
          <SectionEyebrow>Selected bundle</SectionEyebrow>
          <div className="hig-title-3" style={{ marginTop: "var(--space-1)" }}>{current.summary}</div>
          <div className="hig-footnote hig-numeric" style={{ marginTop: "var(--space-2)", color: "var(--colour-label-secondary)" }}>
            {new Date(current.generated_at).toLocaleString("en-AU")} &middot;{" "}
            {current.file_count} files &middot; {(current.size_bytes / 1024).toFixed(1)} KB
            {current.cost_usd > 0 && ` · USD $${current.cost_usd.toFixed(4)} Claude cost`}
          </div>
        </Card>
      )}

      <section style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "var(--space-5)" }}>
        {/* S061: Clickable preview tree */}
        <Card title="Preview Tree">
          {!hasBundle ? (
            <p className="hig-footnote" style={{ color: "var(--colour-label-tertiary)" }}>
              Generate an export above to preview file content.
            </p>
          ) : (
            <div style={{ maxHeight: 420, overflowY: "auto" }}>
              {Object.entries(groups).map(([group, paths]) => (
                <div key={group} style={{ marginBottom: "var(--space-3)" }}>
                  <div
                    className="hig-caption-1"
                    style={{
                      color: "var(--colour-label-tertiary)",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                      marginBottom: "var(--space-1)",
                    }}
                  >
                    {group === "(root)" ? "root" : group + "/"}
                  </div>
                  {paths.map((p) => (
                    <button
                      key={p}
                      onClick={() => openPreview(p)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "var(--space-2)",
                        width: "100%",
                        textAlign: "left",
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        padding: "3px var(--space-2)",
                        borderRadius: "var(--radius-sm)",
                        color: "var(--colour-accent)",
                        fontFamily: "'SF Mono', ui-monospace, monospace",
                        fontSize: "var(--type-footnote)",
                        lineHeight: "var(--lead-footnote)",
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--colour-accent-tint-bg)")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "none")}
                    >
                      <span style={{ color: "var(--colour-label-tertiary)", width: 18, flexShrink: 0 }}>
                        {fileIcon(p)}
                      </span>
                      {p.split("/").pop()}
                    </button>
                  ))}
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="History">
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {data?.exports.map((e, i) => {
              const active = selected === e.export_id;
              return (
                <li
                  key={e.export_id}
                  style={{
                    padding: "var(--space-3) 0",
                    borderTop: i === 0 ? "none" : "1px solid var(--colour-separator)",
                    display: "flex",
                    alignItems: "center",
                    gap: "var(--space-3)",
                    cursor: "pointer",
                  }}
                  onClick={() => setSelected(e.export_id)}
                >
                  <div style={{ flex: 1 }}>
                    <div className="hig-callout" style={{ fontWeight: active ? 600 : 400, color: active ? "var(--colour-accent)" : undefined }}>
                      Export #{e.export_id}
                    </div>
                    <div className="hig-footnote" style={{ color: "var(--colour-label-secondary)" }}>
                      {new Date(e.generated_at).toLocaleDateString("en-AU")} &middot; {e.file_count} files
                    </div>
                  </div>
                  {e.file_count > 0 && e.bundle_path && (
                    <a
                      href={`/api/squarespace/exports/${e.export_id}/download`}
                      download
                      className="hig-footnote"
                      style={{ color: "var(--colour-accent)", fontWeight: 600, textDecoration: "none" }}
                      onClick={(ev) => ev.stopPropagation()}
                    >
                      .zip
                    </a>
                  )}
                </li>
              );
            })}
            {data?.exports.length === 0 && (
              <li className="hig-footnote" style={{ color: "var(--colour-label-tertiary)" }}>
                No exports yet.
              </li>
            )}
          </ul>
        </Card>
      </section>

      {/* S062: Primary download CTA */}
      <div
        data-testid="download-bundle-strip"
        style={{
          display: "flex",
          justifyContent: "flex-end",
          padding: "var(--space-4) 0",
          borderTop: "1px solid var(--colour-separator-opaque)",
        }}
      >
        {hasBundle ? (
          <Button
            href={`/api/squarespace/exports/${current.export_id}/download`}
            download
            variant="filled"
            size="lg"
          >
            Download Bundle (.zip) &darr;
          </Button>
        ) : (
          <Button variant="filled" size="lg" onClick={generate} disabled={busy}>
            {busy ? "Generating..." : "Generate + Download"}
          </Button>
        )}
      </div>

      {/* S061: File preview modal */}
      <dialog
        ref={dialogRef}
        style={{
          border: "none",
          borderRadius: "var(--radius-lg)",
          boxShadow: "0 20px 60px rgba(0,0,0,0.25)",
          padding: 0,
          maxWidth: "min(720px, 90vw)",
          width: "100%",
          maxHeight: "80vh",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          background: "var(--colour-bg-system)",
          color: "var(--colour-label)",
        }}
        onClick={(e) => { if (e.target === dialogRef.current) closePreview(); }}
      >
        {/* Modal header */}
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "var(--space-4) var(--space-5)",
          borderBottom: "1px solid var(--colour-separator-opaque)",
          flexShrink: 0,
        }}>
          <div>
            <div className="hig-headline">{previewPath?.split("/").pop()}</div>
            <div className="hig-footnote" style={{ color: "var(--colour-label-secondary)", fontFamily: "'SF Mono', monospace" }}>
              {previewPath}
            </div>
          </div>
          <button
            onClick={closePreview}
            style={{
              background: "var(--colour-bg-system-secondary)",
              border: "none",
              borderRadius: "var(--radius-md)",
              padding: "var(--space-2) var(--space-3)",
              cursor: "pointer",
              color: "var(--colour-label-secondary)",
              fontSize: "var(--type-callout)",
            }}
          >
            Close
          </button>
        </div>

        {/* Modal body */}
        <div style={{
          flex: 1,
          overflowY: "auto",
          padding: "var(--space-4) var(--space-5)",
        }}>
          {previewLoading ? (
            <p className="hig-body" style={{ color: "var(--colour-label-secondary)" }}>Loading...</p>
          ) : (
            <pre style={{
              margin: 0,
              fontFamily: previewPath?.endsWith(".json")
                ? "'SF Mono', ui-monospace, monospace"
                : "inherit",
              fontSize: "var(--type-footnote)",
              lineHeight: 1.6,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}>
              {previewContent}
            </pre>
          )}
        </div>
      </dialog>
    </div>
  );
}
