/**
 * Decipher native audit-take page. Replaces the Google Form with an
 * HIG-styled, on-brand experience that posts straight into the schema.
 *
 * Mirrors the verbatim Media Sales DNA Audit (audit_version code
 * 'media_sales_v1') seeded by scripts/seed_media_sales_dna_v1.py.
 */
import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api";
import { Logo } from "../components/Logo";
import { Card, Button } from "../components/Card";

type Question = {
  question_id: number;
  sequence: number;
  dimension: string;
  archetype_signal: string | null;
  prompt: string;
  response_type: string;
  response_meta: {
    options?: string[];
    scoring?: number[];
    archetype_by_position?: string[] | null;
    source_form?: string;
  } | null;
};
type VersionPayload = {
  version: { audit_version_id: number; code: string; name: string };
  questions: Question[];
};

type Step = "intro" | "question" | "done";

type CompleteResult = {
  ok: boolean;
  audit_id: number;
  score?: {
    archetype: string;
    archetype_description?: string | null;
    eq_identity: string | null;
    scores_100: Record<string, number>;
    bands: Record<string, string>;
    confidence: number;
  };
  report?: { report_id: number; pdf_path: string; version: number };
};

export default function AuditTake() {
  const { auditId: paramAuditId } = useParams();
  const nav = useNavigate();

  const [version, setVersion] = useState<VersionPayload | null>(null);
  const [auditId, setAuditId] = useState<number | null>(paramAuditId ? Number(paramAuditId) : null);
  const [step, setStep] = useState<Step>(paramAuditId ? "question" : "intro");
  const [idx, setIdx] = useState(0);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<CompleteResult | null>(null);

  // Intro fields
  const [email, setEmail]       = useState("");
  const [name,  setName]        = useState("");
  const [jobTitle, setJobTitle] = useState(""); const [company, setCompany] = useState("");
  
  
  
  const [startedAt, setStartedAt] = useState<number>(Date.now());

  useEffect(() => {
    api<VersionPayload>("/api/audit/versions/media_sales_v1/questions")
      .then(setVersion);
  }, []);

  const questions = useMemo(
    () => (version?.questions ?? []).filter((q) => q.response_type === "choice"),
    [version],
  );
  const q = questions[idx];
  const progress = questions.length ? (idx / questions.length) : 0;

  async function start() {
    if (!email.trim() || !name.trim()) return;
    setBusy(true);
    try {
      const body = {
        email:        email.trim(),
        name:         name.trim(),
        job_title:    jobTitle.trim() || null,
        company:      company.trim() || null,
        version_code: "media_sales_v1",       team_id: (() => { const t = new URLSearchParams(window.location.search).get("team"); return t ? Number(t) : null; })(),
      };
      const s = await fetch("/api/audit/start", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); const sd = await s.json(); if (!s.ok) { alert(sd.detail || "Something went wrong. Please try again."); return; } setAuditId(sd.audit_id); setStep("question"); setStartedAt(Date.now()); nav(`/audit/${sd.audit_id}`, { replace: true }); } finally {
      setBusy(false);
    }
  }

  async function answer(optionIndex: number) {
    if (!q || !auditId) return;
    setBusy(true);
    try {
      await api(`/api/audit/${auditId}/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question_id: q.question_id,
          value: optionIndex,
          elapsed_ms: Date.now() - startedAt,
        }),
      });
      setStartedAt(Date.now());
      if (idx + 1 >= questions.length) {
        const res = await api<CompleteResult>(`/api/audit/${auditId}/complete`, { method: "POST" });
        setResult(res);
        setStep("done");
      } else {
        setIdx(idx + 1);
      }
    } finally {
      setBusy(false);
    }
  }

  if (!version) return <p className="hig-footnote">Loading audit...</p>;

  return (
    <div
      style={{
        minHeight: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "var(--space-5)",
      }}
    >
      <div style={{ width: "100%", maxWidth: 760, display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
        {/* Header */}
        <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "var(--space-4)" }}>
          <Logo height={32} />
          
        </header>

        {/* Progress bar */}
        {step === "question" && (
          <div>
            <div
              style={{
                height: 6,
                background: "var(--colour-fill-quaternary)",
                borderRadius: "var(--radius-pill)",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${Math.round(progress * 100)}%`,
                  background: "var(--colour-accent)",
                  transition: "width var(--duration-base) var(--easing)",
                }}
              />
            </div>
            <div className="hig-caption-1" style={{ marginTop: 6, textAlign: "right" }}>
              Question {idx + 1} of {questions.length}
            </div>
          </div>
        )}

        {step === "intro" && (
          <Card>
            <h1 className="hig-large-title" style={{ margin: 0 }}>{version.version.name}</h1>
            <p className="hig-body" style={{ color: "var(--colour-label)", marginTop: "var(--space-3)" }}>
              This assessment is confidential. Answer honestly. There are no right
              or wrong answers. {questions.length} questions, roughly 7-10 minutes.
            </p>
            <div style={{ display: "grid", gap: "var(--space-3)", marginTop: "var(--space-5)" }}>
              <Field label="Full name" value={name} onChange={setName} placeholder="Your name" />
              <Field label="Work email" value={email} onChange={setEmail} placeholder="you@company.com" type="email" />
              <Field label="Job title" value={jobTitle} onChange={setJobTitle} placeholder="Sales rep, Sales Director, etc." /> <Field label="Company" value={company} onChange={setCompany} placeholder="Your company name" />
              
            </div>
            <div style={{ marginTop: "var(--space-5)", display: "flex", justifyContent: "flex-end" }}>
              <Button onClick={start} variant="filled" size="lg">
                {busy ? "Processing..." : "Begin audit →"}
              </Button>
            </div>
          </Card>
        )}

        {step === "question" && q && (
          <Card>
            <div className="hig-caption-1" style={{ color: "var(--colour-label-secondary)" }}>
              {q.dimension.replace("_", " ")} {q.archetype_signal ? `· archetype` : ""}
            </div>
            <h2 className="hig-title-2" style={{ margin: "var(--space-2) 0 var(--space-4) 0" }}>
              {q.prompt}
            </h2>
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
              {(q.response_meta?.options ?? []).map((opt, i) => (
                <button
                  key={i}
                  disabled={busy}
                  onClick={() => answer(i)}
                  style={{
                    textAlign: "left",
                    padding: "var(--space-3) var(--space-4)",
                    background: "var(--colour-bg-system)",
                    border: "1px solid var(--colour-separator-opaque)",
                    borderRadius: "var(--radius-md)",
                    cursor: busy ? "wait" : "pointer",
                    fontSize: "var(--type-callout)",
                    fontFamily: "inherit",
                    color: "var(--colour-label)",
                    transition: "background var(--duration-fast), border-color var(--duration-fast)",
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = "var(--colour-accent-tint-bg)"; e.currentTarget.style.borderColor = "var(--colour-accent)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = "var(--colour-bg-system)"; e.currentTarget.style.borderColor = "var(--colour-separator-opaque)"; }}
                >
                  <span style={{ color: "var(--colour-label-tertiary)", marginRight: "var(--space-3)", fontWeight: 700 }}>
                    {String.fromCharCode(65 + i)}.
                  </span>
                  {opt}
                </button>
              ))}
            </div>
          </Card>
        )}

        {step === "done" && <DoneCard auditId={auditId} result={result} />}

        <footer className="hig-footnote" style={{ textAlign: "center", color: "var(--colour-label-tertiary)", padding: "var(--space-5) 0" }}>
          decipher.com.au · {version.version.name}
        </footer>
      </div>
    </div>
  );
}

const DIM_LABEL: Record<string, string> = {
  cognitive_empathy:    "Cognitive Empathy",
  eq:                   "Emotional Intelligence",
  pressure_composure:   "Pressure Composure",
  narrative_persuasion: "Narrative Persuasion",
  storytelling:         "Narrative Persuasion",
};
const BAND_COLOUR: Record<string, string> = {
  elite:      "var(--colour-band-elite)",
  performing: "var(--colour-band-performing)",
  practising: "var(--colour-band-practising)",
  developing: "var(--colour-band-developing)",
};
const EQ_IDENTITY_LABEL: Record<string, string> = {
  regulator: "Regulator", edge_builder: "Edge Builder",
  observer:  "Observer",  namer:        "Namer",
};

function DoneCard({ auditId, result }: { auditId: number | null; result: CompleteResult | null }) {
  if (!result || !result.score) {
    return (
      <Card>
        <h1 className="hig-large-title" style={{ margin: 0 }}>Audit submitted.</h1>
        <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-3)" }}>
          Thank you. Your responses are stored against audit #{auditId}. Your
          personalised Decipher DNA report will be emailed to you once scoring
          and report generation complete.
        </p>
      </Card>
    );
  }
  const s = result.score;
  const order = ["cognitive_empathy", "eq", "pressure_composure", "narrative_persuasion"];
  return (
    <Card>
      <h1 className="hig-large-title" style={{ margin: 0 }}>Your DNA result</h1>
      <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-3)" }}>
        Audit #{auditId} scored. Below is the headline; the full 3-page report
        is ready to download.
      </p>

      <div style={{ background: "var(--colour-accent)", color: "#FFFFFF",
                    borderRadius: "var(--radius-md)", padding: "var(--space-4)",
                    marginTop: "var(--space-4)" }}>
        <div className="hig-caption-1" style={{ opacity: 0.85, textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Archetype · {Math.round(s.confidence * 100)}% confidence
        </div>
        <div className="hig-title-1" style={{ marginTop: 4, fontWeight: 700 }}>{s.archetype}</div>
        {s.archetype_description && (
          <div className="hig-callout" style={{ opacity: 0.92, marginTop: 6 }}>
            {s.archetype_description}
          </div>
        )}
        {s.eq_identity && (
          <div className="hig-callout" style={{ opacity: 0.92, marginTop: 6 }}>
            EQ identity: {EQ_IDENTITY_LABEL[s.eq_identity] ?? s.eq_identity}
          </div>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)",
                    gap: "var(--space-3)", marginTop: "var(--space-4)" }}>
        {order.map((trait) => {
          const score = s.scores_100[trait] ?? 0;
          const dbDim = trait === "narrative_persuasion" ? "storytelling" : trait;
          const band = s.bands[dbDim] ?? "-";
          return (
            <div key={trait} style={{
              background: "var(--colour-bg-system)",
              border: "1px solid var(--colour-separator-opaque)",
              borderRadius: "var(--radius-md)", padding: "var(--space-4)",
            }}>
              <div className="hig-caption-1" style={{ color: "var(--colour-label-secondary)",
                                                       textTransform: "uppercase", letterSpacing: "0.04em" }}>
                {DIM_LABEL[trait]}
              </div>
              <div className="hig-large-title hig-numeric" style={{ marginTop: 4 }}>
                {score.toFixed(1)}<span className="hig-body" style={{ color: "var(--colour-label-tertiary)" }}> /100</span>
              </div>
              <div style={{ marginTop: "var(--space-2)" }}>
                <span style={{ background: BAND_COLOUR[band] ?? "var(--colour-label-tertiary)",
                                color: "#FFFFFF", fontSize: "var(--type-caption-1)",
                                padding: "2px 10px", borderRadius: "var(--radius-pill)",
                                fontWeight: 600, textTransform: "capitalize" }}>
                  {band}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {result.report && (
        <div style={{ marginTop: "var(--space-5)", display: "flex", justifyContent: "flex-end" }}>
          <Button href={`/api/reports/${result.report.report_id}/download`} variant="filled" size="lg">
            Download full report (PDF) ↓
          </Button>
        </div>
      )}
    </Card>
  );
}

function Field({
  label, value, onChange, placeholder, type = "text",
}: {
  label: string;
  value: string;
  onChange: (s: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span className="hig-caption-1" style={{ color: "var(--colour-label)" }}>{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder} onMouseEnter={(e) => { e.currentTarget.style.background = "var(--colour-accent-tint-bg)"; e.currentTarget.style.borderColor = "var(--colour-accent)"; }} onMouseLeave={(e) => { e.currentTarget.style.background = "#ffffff"; e.currentTarget.style.borderColor = "var(--colour-separator-opaque)"; }} onFocus={(e) => { e.currentTarget.style.background = "var(--colour-accent-tint-bg)"; e.currentTarget.style.borderColor = "var(--colour-accent)"; }} onBlur={(e) => { e.currentTarget.style.background = "#ffffff"; e.currentTarget.style.borderColor = "var(--colour-separator-opaque)"; }}
        style={{
          height: 40,
          padding: "0 var(--space-3)",
          border: "1px solid var(--colour-separator-opaque)",
          borderRadius: "var(--radius-sm)",
          background: "#ffffff",
          color: "var(--colour-label)",
          fontSize: "var(--type-body)",
          fontFamily: "inherit",
        }}
      />
    </label>
  );
}
