import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { Card, SectionEyebrow, Button } from "../components/Card";
import { BandBar } from "../components/BandBar";

type Company = {
  company_id: number;
  name: string;
  industry: string | null;
  n_teams: number;
  n_respondents: number;
  avg_score_100: number;
  elite_count: number;
  at_risk_count: number;
  band_elite: number;
  band_performing: number;
  band_practising: number;
  band_developing: number;
};

export default function Companies() {
  const { me } = useAuth();
  const [rows, setRows] = useState<Company[] | null>(null);
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [n, setN] = useState({ name: "", industry: "", contact_name: "", contact_email: "", contact_mobile: "", website: "" });

  function refresh() {
    api<{ companies: Company[] }>("/api/companies").then((d) => setRows(d.companies));
  }
  useEffect(() => { refresh(); }, []);

  async function create() {
    if (!n.name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api("/api/companies", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: n.name.trim(), industry: n.industry || null,
          contact_name: n.contact_name || null, contact_email: n.contact_email || null,
          contact_mobile: n.contact_mobile || null, website: n.website || null,
        }),
      });
      setAdding(false);
      setN({ name: "", industry: "", contact_name: "", contact_email: "", contact_mobile: "", website: "" });
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create company. Please try again.");
    } finally { setBusy(false); }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)", maxWidth: 1400 }}>
      <header style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "var(--space-4)" }}>
        <div>
          <h1 className="hig-large-title" style={{ margin: 0 }}>Companies</h1>
          <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-2)" }}>
            Companies roll up many teams. Click in to see every team under a company, all scoped strictly to that company.
          </p>
        </div>
        <Button variant="filled" size="md" onClick={() => setAdding(v => !v)}>
          {adding ? "Cancel" : "Add company +"}
        </Button>
      </header>

      {adding && (
        <Card title="New Company">
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
            gap: "var(--space-3)",
          }}>
            {([["Company name","name","e.g. Atlas Media Group"],
               ["Industry","industry","media / pharma / tech"],
               ["Contact name","contact_name","Primary contact"],
               ["Contact email","contact_email","contact@company.com"],
               ["Mobile","contact_mobile","04xx xxx xxx"],
               ["Website","website","https://company.com.au"]] as const).map(([lbl, key, ph]) => (
              <label key={key} style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 0 }}>
                <span className="hig-caption-1">{lbl}</span>
                <input value={n[key]}
                  onChange={(e) => setN({ ...n, [key]: e.target.value })}
                  placeholder={ph}
                  style={{ height: 36, padding: "0 var(--space-3)",
                    border: "1px solid var(--colour-separator-opaque)",
                    borderRadius: "var(--radius-sm)",
                    background: "var(--colour-bg-system)",
                    color: "var(--colour-label)",
                    fontSize: "var(--type-callout)", fontFamily: "inherit",
                    width: "100%", boxSizing: "border-box" }} />
              </label>
            ))}
          </div>
          {error && (
            <div className="hig-caption-1" style={{ color: "#D92D20", marginTop: "var(--space-3)" }}>
              {error}
            </div>
          )}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "var(--space-2)",
            marginTop: "var(--space-4)", paddingTop: "var(--space-4)",
            borderTop: "1px solid var(--colour-separator)" }}>
            <Button variant="plain" size="md" onClick={() => setAdding(false)}>Cancel</Button>
            <Button variant="filled" size="md" onClick={create}>{busy ? "Saving..." : "Create company"}</Button>
          </div>
        </Card>
      )}

      {rows?.map((c) => {
        const isDemo = c.name.startsWith("Demo:");
        const display = isDemo ? c.name.replace(/^Demo:\s*/, "") : c.name;
        return (
          <section key={c.company_id} style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
            {/* Big company heading row */}
            <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
              gap: "var(--space-3)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                <Link to={`/companies/${c.company_id}`} style={{ textDecoration: "none", color: "inherit" }}>
                  <h2 className="hig-title-1" style={{ margin: 0, fontWeight: 700, fontSize: 30, letterSpacing: "-0.01em" }}>
                    {display}
                  </h2>
                </Link>
                {isDemo && (
                  <span className="hig-caption-1" style={{
                    background: "var(--colour-accent-tint-bg)", color: "var(--colour-accent)",
                    padding: "3px 10px", borderRadius: 999, fontWeight: 700,
                    textTransform: "uppercase", letterSpacing: "0.06em",
                  }}>Demo</span>
                )}
                {c.industry && (
                  <span className="hig-caption-1" style={{ color: "var(--colour-label-tertiary)",
                    textTransform: "uppercase", letterSpacing: "0.04em" }}>
                    {c.industry}
                  </span>
                )}
              </div>
              <Link to={`/companies/${c.company_id}`}
                style={{ background: "var(--colour-accent)", color: "#FFFFFF",
                  padding: "8px 14px", borderRadius: "var(--radius-sm)", fontWeight: 700,
                  fontSize: "var(--type-callout)", textDecoration: "none" }}>
                Open ›
              </Link>
            </header>

            <Link to={`/companies/${c.company_id}`} style={{ textDecoration: "none", color: "inherit" }}>
              <Card>
                <div style={{ display: "grid", gridTemplateColumns: "0.7fr 0.7fr 0.7fr 0.7fr 1.4fr 24px", gap: "var(--space-5)", alignItems: "center" }}>
                  <Tile label="Teams" value={c.n_teams} />
                  <Tile label="Reps" value={c.n_respondents} />
                  <Tile label="Avg" value={`${c.avg_score_100.toFixed(1)}`} suffix="/100" />
                  <Tile label="Elite / Risk" value={`${c.elite_count} · ${c.at_risk_count}`} />
                  <div style={{ minWidth: 0 }}>
                    <BandBar
                      label="Distribution"
                      elite={c.band_elite}
                      performing={c.band_performing}
                      practising={c.band_practising}
                      developing={c.band_developing}
                    />
                  </div>
                  <span aria-hidden="true" style={{ color: "var(--colour-label-tertiary)", fontSize: "var(--type-title-3)" }}>›</span>
                </div>
              </Card>
            </Link>
          </section>
        );
      })}
    </div>
  );
}

function Tile({ label, value, suffix }: { label: string; value: string | number; suffix?: string }) {
  return (
    <div>
      <div className="hig-caption-1">{label}</div>
      <div className="hig-title-3 hig-numeric" style={{ marginTop: 2 }}>
        {value}{suffix && <span className="hig-footnote" style={{ color: "var(--colour-label-tertiary)", marginLeft: 2 }}>{suffix}</span>}
      </div>
    </div>
  );
}
