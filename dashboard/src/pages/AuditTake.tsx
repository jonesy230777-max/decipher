/**
 * Decipher native audit-take page. Replaces the Google Form with an
 * HIG-styled, on-brand experience that posts straight into the schema.
 *
 * Mirrors the verbatim Media Sales DNA Audit (audit_version code
 * 'media_sales_v1') seeded by scripts/seed_media_sales_dna_v1.py.
 */
import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, downloadFile } from "../api";
import { Card, Button } from "../components/Card";
import { Logo } from "../components/Logo";

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

type VersionSummary = { audit_version_id: number; code: string; name: string };

type AuditStateResponse = {
  audit_id: number;
  status: string;
  version_code: string;
  version_name: string;
  respondent_name: string | null;
  answered_question_ids: number[];
};

/**
 * Client-side memory of an in-progress audit, so a respondent who closes
 * the tab (or never had the /audit/{id} URL to begin with) can still be
 * offered their unfinished audit next time they land on /audit/start.
 * The server (`/api/audit/{id}/state`) remains the source of truth for
 * what was actually answered; this is just enough to find the audit_id
 * again and is discarded once the audit is completed or once it's stale.
 */
const RESUME_KEY = "decipher.audit.inProgress";
const RESUME_MAX_AGE_MS = 30 * 24 * 60 * 60 * 1000; // 30 days

type ResumeState = { auditId: number; versionCode: string; savedAt: number };

function saveResumeState(auditId: number, versionCode: string): void {
  try {
    const state: ResumeState = { auditId, versionCode, savedAt: Date.now() };
    localStorage.setItem(RESUME_KEY, JSON.stringify(state));
  } catch {
    // Private browsing / storage disabled: resume just degrades to "off".
  }
}

function loadResumeState(): ResumeState | null {
  try {
    const raw = localStorage.getItem(RESUME_KEY);
    if (!raw) return null;
    const state = JSON.parse(raw) as ResumeState;
    if (!state?.auditId || !state?.versionCode || !state?.savedAt) return null;
    if (Date.now() - state.savedAt > RESUME_MAX_AGE_MS) return null;
    return state;
  } catch {
    return null;
  }
}

function clearResumeState(): void {
  try {
    localStorage.removeItem(RESUME_KEY);
  } catch {
    // ignore
  }
}

type Step = "intro" | "resume_prompt" | "question" | "done";

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

/**
 * Deterministic per-(audit, question) shuffle of answer-option display
 * positions.
 *
 * Why: a 2026-07 audit of the canonical question bank found that answer
 * order correlates with score — the lowest-scoring option sits first
 * (position A) in ~84% of the 31 scored questions. Showing options in
 * canonical order lets an attentive respondent learn "avoid the first
 * option" as a shortcut, inflating their score without reflecting real
 * trait ability.
 *
 * Fix: shuffle the *displayed* order per respondent/per question, while
 * `answer()` still submits the canonical option index. Scoring
 * (app/dna_scoring.py `_score_from_response` / `_identity_from_response`)
 * already resolves `answer_value` as an index into `response_meta.options`
 * / `options_meta`, completely independent of how it was rendered — so
 * this is a display-only change. No backend, schema, or scoring changes
 * needed.
 *
 * The shuffle is seeded by (audit_id, question_id) so it's stable across
 * re-renders for one respondent's view of one question, but two different
 * respondents (or the same respondent re-auditing later, since audit_id
 * changes) will almost always see a different order for the same question.
 */
function hashSeed(a: number, b: number): number {
  let h = (Math.imul(a, 2654435761) ^ Math.imul(b, 40503)) >>> 0;
  h = Math.imul(h ^ (h >>> 16), 2246822507);
  h = Math.imul(h ^ (h >>> 13), 3266489909);
  return (h ^ (h >>> 16)) >>> 0;
}

function seededShuffleIndices(seed: number, length: number): number[] {
  let s = seed >>> 0;
  const rand = () => {
    s |= 0;
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const arr = Array.from({ length }, (_, i) => i);
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

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
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [jobTitle, setJobTitle] = useState(""); const [company, setCompany] = useState("");
  const [consent, setConsent] = useState(false);

  const [startedAt, setStartedAt] = useState<number>(Date.now());

  const [versionList, setVersionList] = useState<VersionSummary[] | null>(null);
  const [selectedVersionCode, setSelectedVersionCode] = useState<string>(
    () => new URLSearchParams(window.location.search).get("v") || "media_sales_v1"
  );
  // Resume support ---------------------------------------------------
  // audit_id we're resuming into, the questions already answered for it
  // (consumed once to seed `idx`, see effect below), and enough info to
  // show a "welcome back" prompt when we found it via localStorage rather
  // than an explicit /audit/{id} URL.
  const [answeredIds, setAnsweredIds] = useState<Set<number> | null>(null);
  const [resumeInfo, setResumeInfo] = useState<{ versionName: string; answeredCount: number } | null>(null);
  const [resumeChecked, setResumeChecked] = useState(false);
  // True when a /audit/{id} link was opened for an audit that is no
  // longer in_progress -- the link is still valid to click, it just
  // does not reopen the questions. See DoneCard render below.
  const [alreadyCompleted, setAlreadyCompleted] = useState(false);

  useEffect(() => {
    const saved = loadResumeState();
    const candidateId = paramAuditId ? Number(paramAuditId) : saved?.auditId ?? null;
    if (!candidateId) {
      setResumeChecked(true);
      return;
    }
    api<AuditStateResponse>(`/api/audit/${candidateId}/state`)
      .then((s) => {
        if (s.status !== "in_progress") {
          // Already finished (maybe on another device/tab) or not
          // resumable -- nothing to restore.
          clearResumeState();
          if (paramAuditId) {
            // They followed an actual /audit/{id} link (e.g. the emailed
            // resume link) straight to a completed audit -- say so
            // plainly instead of dropping them into a dead question
            // screen. A locally-remembered id with no link, by
            // contrast, just quietly falls back to a fresh intro.
            setAlreadyCompleted(true);
            setStep("done");
          }
          setResumeChecked(true);
          return;
        }
        setAuditId(s.audit_id);
        setSelectedVersionCode(s.version_code);
        setAnsweredIds(new Set(s.answered_question_ids));
        setResumeInfo({ versionName: s.version_name, answeredCount: s.answered_question_ids.length });
        // A direct /audit/{id} link goes straight back into the questions;
        // a locally-remembered audit (no id in the URL) gets an explicit
        // "welcome back" choice instead of silently dropping them mid-way.
        setStep(paramAuditId ? "question" : "resume_prompt");
        setResumeChecked(true);
      })
      .catch(() => {
        clearResumeState();
        setResumeChecked(true);
      });
    // Runs once on mount only -- deliberately not re-checking after that.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    api<{ versions: VersionSummary[] }>("/api/audit/versions")
      .then((d) => setVersionList(d.versions));
  }, []);

  useEffect(() => {
    api<VersionPayload>(`/api/audit/versions/${selectedVersionCode}/questions`)
      .then(setVersion);
  }, [selectedVersionCode]);

  const questions = useMemo(
    () => (version?.questions ?? []).filter((q) => q.response_type === "choice"),
    [version],
  );
  // Deterministic per-audit shuffle of question *order* (not just answer
  // options) so respondents don't answer in fixed trait blocks (Cognitive
  // Empathy, then EQ, then Pressure Composure, ...) -- fixed blocks make it
  // obvious which trait is being probed. Seeded by auditId with a fixed
  // salt so it's stable across re-renders/reloads for one respondent but
  // differs audit to audit. Scoring is keyed by question_id/canonical_trait,
  // not position, so this is a display-only change.
  const shuffledQuestions = useMemo(() => {
    if (!questions.length || auditId == null) return questions;
    const order = seededShuffleIndices(hashSeed(auditId, 8675309), questions.length);
    return order.map((i) => questions[i]);
  }, [questions, auditId]);

  // Once we know which questions were already answered (from /state) and
  // have the shuffled order to lay them out in, jump straight to the
  // first unanswered one instead of restarting at question 1.
  useEffect(() => {
    if (step !== "question" || !answeredIds || !shuffledQuestions.length) return;
    let resumeIdx = 0;
    while (resumeIdx < shuffledQuestions.length && answeredIds.has(shuffledQuestions[resumeIdx].question_id)) {
      resumeIdx++;
    }
    setIdx(resumeIdx);
    setAnsweredIds(null); // consumed -- don't let this fight manual navigation later
  }, [step, answeredIds, shuffledQuestions]);

  const q = shuffledQuestions[idx];
  const progress = shuffledQuestions.length ? (idx / shuffledQuestions.length) : 0;

  // Canonical-index order to render options in for this respondent/question.
  // See hashSeed/seededShuffleIndices above for why this exists.
  const displayOrder = useMemo(() => {
    const n = q?.response_meta?.options?.length ?? 0;
    if (!n) return [];
    if (auditId == null || q == null) return Array.from({ length: n }, (_, i) => i);
    return seededShuffleIndices(hashSeed(auditId, q.question_id), n);
  }, [q, auditId]);

  async function start() {
    if (!email.trim() || !name.trim()) return;
    setBusy(true);
    try {
      const body = {
        email: email.trim(),
        name: name.trim(),
        job_title: jobTitle.trim() || null,
        company: company.trim() || null,
        consent_share_individual: consent,
        version_code: selectedVersionCode, team_id: (() => { const t = new URLSearchParams(window.location.search).get("team"); return t ? Number(t) : null; })(),
        token: new URLSearchParams(window.location.search).get("invite"),
      };
      const s = await fetch("/api/audit/start", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); const sd = await s.json(); if (!s.ok) { alert(sd.detail || "Something went wrong. Please try again."); return; } setAuditId(sd.audit_id); saveResumeState(sd.audit_id, selectedVersionCode); setStep("question"); setStartedAt(Date.now()); nav(`/audit/${sd.audit_id}?v=${selectedVersionCode}`, { replace: true }); } finally {
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
      if (idx + 1 >= shuffledQuestions.length) {
        const res = await api<CompleteResult>(`/api/audit/${auditId}/complete`, { method: "POST" });
        clearResumeState();
        setResult(res);
        setStep("done");
      } else {
        setIdx(idx + 1);
      }
    } finally {
      setBusy(false);
    }
  }

  if (!version || (paramAuditId && !resumeChecked)) return <p className="hig-footnote">Loading audit...</p>;

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
        <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "var(--space-4)", marginTop: 30 }}>
          <Logo height={32} /><span className="hig-headline" style={{ color: "var(--colour-label)", fontWeight: 700 }}>Sales DNA Audit</span>

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
            <div className="hig-caption-1" style={{ marginTop: 6, color: "var(--colour-accent)", textAlign: "right" }}>
              Question {idx + 1} of {shuffledQuestions.length}
            </div>
          </div>
        )}

        {step === "resume_prompt" && resumeInfo && (
          <Card>
            <h1 className="hig-large-title" style={{ margin: 0 }}>Welcome back</h1>
            <p className="hig-body" style={{ color: "var(--colour-label)", marginTop: "var(--space-3)" }}>
              You are partway through the {resumeInfo.versionName}. You have answered{" "}
              {resumeInfo.answeredCount} question{resumeInfo.answeredCount === 1 ? "" : "s"} so far.
            </p>
            <div style={{ marginTop: "var(--space-5)", display: "flex", justifyContent: "flex-end", gap: "var(--space-3)" }}>
              <Button
                onClick={() => {
                  clearResumeState();
                  setAnsweredIds(null);
                  setResumeInfo(null);
                  setAuditId(null);
                  setIdx(0);
                  setStep("intro");
                }}
                variant="plain"
                size="lg"
              >
                Start over
              </Button>
              <Button onClick={() => setStep("question")} variant="filled" size="lg">
                Continue where you left off →
              </Button>
            </div>
          </Card>
        )}

        {step === "intro" && (
          <Card>
            <h1 className="hig-large-title" style={{ margin: 0 }}>{version.version.name}</h1>
            <p className="hig-body" style={{ color: "var(--colour-label)", marginTop: "var(--space-3)" }}>
                        Before you begin, a few quick notes.
                        <br /><br />
                        This audit takes about 10 to 15 minutes. There are {questions.length} questions, each describing a real sales situation.
                        <br /><br />
                        Choose one answer per question: the one that best reflects what you'd actually do, not what sounds most correct or impressive. There are no right answers here, only honest ones.
                        <br /><br />
                        If more than one option feels true, go with your first instinct: the response that's most automatic for you under normal pressure. That instinct is exactly what this audit is designed to measure.
                        <br /><br />
                        Your results will generate a personalised Sales DNA profile, showing your strengths across four key trait areas and where your biggest development opportunity lies.<br /><br />This audit comes in three versions, built for different sales motions. Choose the one that matches your role below.<br /><br /><strong>Media Sales:</strong> for sales professionals managing existing client relationships, pitching campaigns, renewing accounts, and growing revenue with warm, ongoing contacts.<br /><br /><strong>The Hunter:</strong> for sales professionals who generate their own pipeline. They cold call to book meetings, then present and close the sale online or face to face.<br /><br /><strong>Charity & NFP Fundraising:</strong> for phone fundraisers calling potential donors on behalf of a charity, covering the donor call from opener through to the ask and objection handling.
                        <br /><br />
                        Ready? Let's begin.
            </p>
            {versionList && versionList.filter((v) => v.code === "media_sales_v1" || v.code === "generic_sales_v2" || v.code === "charity_fundraising_v1" || v.code === "retail_media_v1").length > 1 && (
              <div style={{ marginTop: "var(--space-4)" }}>
                <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  <span className="hig-caption-1" style={{ color: "var(--colour-label)" }}>Audit type</span>
                  <select
                    value={selectedVersionCode}
                    onChange={(e) => setSelectedVersionCode(e.target.value)}
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
                  >
                 {versionList.filter((v) => v.code === "media_sales_v1" || v.code === "generic_sales_v2" || v.code === "charity_fundraising_v1" || v.code === "retail_media_v1").map((v) => (
<option key={v.code} value={v.code}>{v.code === "media_sales_v1" ? "Media Sales" : v.code === "generic_sales_v2" ? "The Hunter" : v.code === "charity_fundraising_v1" ? "Charity & NFP Fundraising" : v.code === "retail_media_v1" ? "Retail Media Sales" : v.name}</option>                   
                    ))}
                  </select>
                </label>
              </div>
            )}
            <div style={{ display: "grid", gap: "var(--space-3)", marginTop: "var(--space-5)" }}>
              <Field label="Full name" value={name} onChange={setName} placeholder="Your name" />
              <Field label="Work email" value={email} onChange={setEmail} placeholder="you@company.com" type="email" />
              <Field label="Job title" value={jobTitle} onChange={setJobTitle} placeholder="Sales rep, Sales Director, etc." /> <Field label="Company" value={company} onChange={setCompany} placeholder="Your company name" />

            </div>
            <label style={{ display: "flex", alignItems: "flex-start", gap: 8, marginTop: "var(--space-4)", cursor: "pointer" }}>
              <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} style={{ marginTop: 3 }} />
              <span className="hig-caption-1" style={{ color: "var(--colour-label)" }}>
                I'm OK with my name and email being shown next to my results in team leaderboards and reports. If left unchecked, my results will be shown anonymised.
              </span>
            </label>
            <div style={{ marginTop: "var(--space-5)", display: "flex", justifyContent: "flex-end" }}>
              <Button onClick={start} variant="filled" size="lg">
                {busy ? "Processing..." : "Begin audit →"}
              </Button>
            </div>
          </Card>
        )}

        {step === "question" && q && (
          <Card>
            <h2 className="hig-title-2" style={{ margin: "var(--space-2) 0 var(--space-4) 0" }}>
              {q.prompt}
            </h2>
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
              {displayOrder.map((canonicalIdx, i) => (
                <button
                  key={canonicalIdx}
                  disabled={busy} onClick={() => answer(canonicalIdx)} className="audit-option-btn"

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


                >
                  <span style={{ color: "var(--colour-label-tertiary)", marginRight: "var(--space-3)", fontWeight: 700 }}>
                    {String.fromCharCode(65 + i)}.
                  </span>
                  {q.response_meta?.options?.[canonicalIdx] ?? ""}
                </button>
              ))}
            </div>
            <p className="hig-footnote" style={{ color: "var(--colour-label)", marginTop: "var(--space-4)", textAlign: "center" }}>Choose one, go with your first instinct.</p>
          </Card>
        )}

        {step === "done" && (
          alreadyCompleted
            ? <AlreadyCompletedCard />
            : <DoneCard auditId={auditId} result={result} />
        )}

        <footer className="hig-footnote" style={{ textAlign: "center", color: "var(--colour-label)", padding: "var(--space-5) 0" }}>
          deciphersales.com.au · {version.version.name}
        </footer>
      </div>
    </div>
  );
}

const DIM_LABEL: Record<string, string> = {
  cognitive_empathy: "Cognitive Empathy",
  eq: "Emotional Intelligence",
  pressure_composure: "Pressure Composure",
  narrative_persuasion: "Narrative Persuasion",
  storytelling: "Narrative Persuasion",
};
const BAND_COLOUR: Record<string, string> = {
  elite: "var(--colour-band-elite)",
  performing: "var(--colour-band-performing)",
  practising: "var(--colour-band-practising)",
  developing: "var(--colour-band-developing)",
};
const EQ_IDENTITY_LABEL: Record<string, string> = {
  regulator: "Regulator", edge_builder: "Edge Builder",
  observer: "Observer", namer: "Namer",
};

function AlreadyCompletedCard() {
  return (
    <Card>
      <h1 className="hig-large-title" style={{ margin: 0 }}>Already completed</h1>
      <p className="hig-body" style={{ color: "var(--colour-label)", marginTop: "var(--space-3)" }}>
        This audit has already been submitted, so this link will not reopen it.
        Your results were sent by email -- check your inbox (and spam folder) if
        you have not seen them yet.
      </p>
    </Card>
  );
}

function DoneCard({ auditId, result }: { auditId: number | null; result: CompleteResult | null }) {
  if (!result || !result.score) {
    return (
      <Card>
        <h1 className="hig-large-title" style={{ margin: 0 }}>Audit submitted.</h1>
        <p className="hig-body" style={{ color: "var(--colour-label)", marginTop: "var(--space-3)" }}>
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
          <Button onClick={() => downloadFile(`/api/reports/${result.report!.report_id}/download`, `report-${result.report!.report_id}.pdf`)} variant="filled" size="lg">
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
        placeholder={placeholder}   onFocus={(e) => { e.currentTarget.style.background = "var(--colour-accent-tint-bg)"; e.currentTarget.style.borderColor = "var(--colour-accent)"; }} onBlur={(e) => { e.currentTarget.style.background = "#ffffff"; e.currentTarget.style.borderColor = "var(--colour-separator-opaque)"; }}
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
