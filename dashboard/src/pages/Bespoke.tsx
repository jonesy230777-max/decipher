import { useEffect, useState } from "react";
import { api } from "../api";
import { Button, Card } from "../components/Card";

type Bespoke = {
  bespoke_client_id: number;
  client_name: string;
  unique_url_slug: string;
  estimated_value: number | null;
  status: "draft" | "active" | "archived";
  created_at: string;
};

type Industry = { industry_id: number; code: string; name: string };

const STATUS_COLOUR: Record<Bespoke["status"], string> = {
  draft:    "var(--colour-label-tertiary)",
  active:   "var(--colour-system-green)",
  archived: "var(--colour-label-tertiary)",
};

const EMPTY = { client_name: "", brief: "", industry_code: "", estimated_value: "", primary_colour: "" };

export default function Bespoke() {
  const [rows, setRows]         = useState<Bespoke[] | null>(null);
  const [industries, setIndustries] = useState<Industry[]>([]);
  const [showing, setShowing]   = useState(false);
  const [form, setForm]         = useState(EMPTY);
  const [busy, setBusy]         = useState(false);
  const [result, setResult]     = useState<{ slug: string; n: number } | null>(null);
  const [err, setErr]           = useState<string | null>(null);

  function refresh() {
    api<{ bespoke: Bespoke[] }>("/api/bespoke").then((d) => setRows(d.bespoke));
  }
  useEffect(() => {
    refresh();
    api<{ industries: Industry[] }>("/api/industries").then((d) => setIndustries(d.industries));
  }, []);

  const totalPipeline = (rows ?? [])
    .filter((r) => r.status === "active")
    .reduce((acc, r) => acc + (r.estimated_value ?? 0), 0);

  async function submit() {
    if (!form.client_name.trim() || !form.brief.trim()) return;
    setBusy(true);
    setErr(null);
    setResult(null);
    try { 
      const json = await api<{ unique_url_slug: string; n_questions: number }>("/api/bespoke", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                          client_name: form.client_name.trim(),
                          brief: form.brief.trim(),
                          industry_code: form.industry_code || null,
                          estimated_value: form.estimated_value ? parseFloat(form.estimated_value) : null,
                          primary_colour: form.primary_colour || null,
              }),
    });
               setResult({ slug: json.unique_url_slug, n: json.n_questions });
               setForm(EMPTY);
               refresh();
    } catch (e: unknown) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ maxWidth: 1100, display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
      <header style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "var(--space-4)" }}>
        <div>
          <h1 className="hig-large-title" style={{ margin: 0 }}>Bespoke clients</h1>
          <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-2)" }}>
            Custom audits and tailored engagements. Active pipeline:{" "}
            <strong className="hig-numeric">AUD ${totalPipeline.toLocaleString("en-AU")}</strong>.
          </p>
        </div>
        <Button variant="filled" size="md" onClick={() => { setShowing(v => !v); setResult(null); setErr(null); }}>
          {showing ? "Cancel" : "+ New bespoke client"}
        </Button>
      </header>

      {showing && (
        <Card>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
            <div>
              <label className="hig-caption-1" style={{ display: "block", marginBottom: "var(--space-1)", textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--colour-label-secondary)" }}>
                Client name *
              </label>
              <input
                className="hig-body"
                style={inputStyle}
                value={form.client_name}
                onChange={e => setForm(f => ({ ...f, client_name: e.target.value }))}
                placeholder="e.g. Northwind Pharma"
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)" }}>
              <div>
                <label className="hig-caption-1" style={labelStyle}>Industry</label>
                <select
                  className="hig-body"
                  style={inputStyle}
                  value={form.industry_code}
                  onChange={e => setForm(f => ({ ...f, industry_code: e.target.value }))}
                >
                  <option value="">-- Select --</option>
                  {industries.map(i => <option key={i.code} value={i.code}>{i.name}</option>)}
                </select>
              </div>
              <div>
                <label className="hig-caption-1" style={labelStyle}>Estimated value (AUD)</label>
                <input
                  className="hig-body hig-numeric"
                  style={inputStyle}
                  type="number"
                  min="0"
                  step="500"
                  value={form.estimated_value}
                  onChange={e => setForm(f => ({ ...f, estimated_value: e.target.value }))}
                  placeholder="e.g. 28500"
                />
              </div>
            </div>

            <div>
              <label className="hig-caption-1" style={labelStyle}>Primary brand colour (hex)</label>
              <input
                className="hig-body hig-numeric"
                style={{ ...inputStyle, width: 160 }}
                value={form.primary_colour}
                onChange={e => setForm(f => ({ ...f, primary_colour: e.target.value }))}
                placeholder="#007AFF"
              />
            </div>

            <div>
              <label className="hig-caption-1" style={labelStyle}>
                Client brief * — describe their sales context, team challenges, and what you want the audit to surface
              </label>
              <textarea
                className="hig-body"
                style={{ ...inputStyle, minHeight: 140, resize: "vertical" }}
                value={form.brief}
                onChange={e => setForm(f => ({ ...f, brief: e.target.value }))}
                placeholder="e.g. Northwind is a pharma rep team of 40, calling on GPs and specialists. Their biggest challenge is objection handling around evidence base and pricing..."
              />
            </div>

            {err && (
              <div className="hig-callout" style={{ color: "var(--colour-system-red)", padding: "var(--space-3)", background: "color-mix(in srgb, var(--colour-system-red) 10%, transparent)", borderRadius: "var(--radius-md)" }}>
                {err}
              </div>
            )}
            {result && (
              <div className="hig-callout" style={{ color: "var(--colour-system-green)", padding: "var(--space-3)", background: "color-mix(in srgb, var(--colour-system-green) 10%, transparent)", borderRadius: "var(--radius-md)" }}>
                Created. {result.n} questions generated. Audit URL: <strong>/audit/{result.slug}</strong>
              </div>
            )}

            <div style={{ display: "flex", gap: "var(--space-3)" }}>
              <Button variant="filled" size="md" onClick={submit} disabled={busy || !form.client_name || !form.brief}>
                {busy ? "Generating questions..." : "Generate audit"}
              </Button>
              <Button variant="ghost" size="md" onClick={() => { setShowing(false); setErr(null); setResult(null); }}>
                Cancel
              </Button>
            </div>
            {busy && (
              <p className="hig-footnote" style={{ color: "var(--colour-label-tertiary)" }}>
                Claude is generating bespoke questions from the brief. This takes 10-20 seconds.
              </p>
            )}
          </div>
        </Card>
      )}

      <ul
        style={{
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
              <div className="hig-footnote" style={{ color: "var(--colour-label-secondary)" }}>/audit/{r.unique_url_slug}</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ color: STATUS_COLOUR[r.status], textTransform: "capitalize", fontWeight: 600 }} className="hig-callout">
                {r.status}
              </div>
              <div className="hig-numeric hig-footnote" style={{ color: "var(--colour-label-secondary)" }}>
                {r.estimated_value ? `AUD $${r.estimated_value.toLocaleString("en-AU")}` : "·"}
              </div>
            </div>
          </li>
        ))}
        {rows?.length === 0 && (
          <li style={{ padding: "var(--space-6)", textAlign: "center", color: "var(--colour-label-tertiary)" }} className="hig-callout">
            No bespoke clients yet. Create one above.
          </li>
        )}
      </ul>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "var(--space-2) var(--space-3)",
  border: "1px solid var(--colour-separator-opaque)",
  borderRadius: "var(--radius-md)",
  background: "var(--colour-bg-system)",
  color: "var(--colour-label)",
  fontSize: "var(--type-body)",
  lineHeight: "var(--lead-body)",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  marginBottom: "var(--space-1)",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  color: "var(--colour-label-secondary)",
};
