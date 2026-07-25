import { useEffect, useRef, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { api } from "../api";

type Turn = { who: "you" | "ai"; text: string };

export function AiAssistant() {
  const loc = useLocation();
  const params = useParams();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState("");
  const [history, setHistory] = useState<Turn[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50);
  }, [open]);

  async function ask() {
    const text = q.trim();
    if (!text) return;
    setHistory((h) => [...h, { who: "you", text }]);
    setQ("");
    setBusy(true);
    try {
    const json = await api<{ answer: string }>("/api/ai/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        q: text,
        page: loc.pathname,
        team_id: params.teamId ? Number(params.teamId) : null,
        company_id: params.companyId ? Number(params.companyId) : null,
      }),
    });
      setHistory((h) => [...h, { who: "ai", text: json.answer ?? "(empty)" }]);
    } catch (e) {
      setHistory((h) => [...h, { who: "ai", text: `Error: ${String(e)}` }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen((v) => !v)}
        title="Ask AI about this page (⌘/)"
        aria-label="Open AI assistant"
        style={{
          position: "fixed",
          right: "var(--space-5)",
          bottom: "var(--space-5)",
          width: 52,
          height: 52,
          borderRadius: "50%",
          background: "var(--colour-accent)",
          color: "#FFFFFF",
          border: "none",
          cursor: "pointer",
          boxShadow: "var(--shadow-2)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 22,
          fontWeight: 700,
          zIndex: 70,
        }}
      >
        ✦
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="AI assistant"
          style={{
            position: "fixed",
            right: "var(--space-5)",
            bottom: "calc(var(--space-5) + 60px)",
            width: 360,
            maxHeight: "70vh",
            display: "flex",
            flexDirection: "column",
            background: "var(--colour-bg-system)",
            border: "1px solid var(--colour-separator-opaque)",
            borderRadius: "var(--radius-lg)",
            boxShadow: "var(--shadow-2)",
            zIndex: 70,
            overflow: "hidden",
          }}
        >
          <header
            style={{
              padding: "var(--space-3) var(--space-4)",
              borderBottom: "1px solid var(--colour-separator)",
              background: "var(--colour-bg-system-secondary)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <span className="hig-headline">Ask AI about this page</span>
            <button
              onClick={() => setOpen(false)}
              aria-label="Close"
              style={{
                background: "transparent", border: "none",
                color: "var(--colour-label-secondary)", cursor: "pointer",
                fontSize: 18, lineHeight: 1,
              }}
            >×</button>
          </header>

          <div
            style={{
              flex: 1,
              padding: "var(--space-3)",
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              gap: "var(--space-2)",
            }}
          >
            {history.length === 0 && (
              <p className="hig-footnote" style={{ margin: 0 }}>
                Try: "who is at risk?", "elite count", "pipeline value", "top archetype".
              </p>
            )}
            {history.map((t, i) => (
              <div
                key={i}
                className="hig-callout"
                style={{
                  alignSelf: t.who === "you" ? "flex-end" : "flex-start",
                  maxWidth: "85%",
                  padding: "var(--space-2) var(--space-3)",
                  borderRadius: "var(--radius-md)",
                  background: t.who === "you" ? "var(--colour-accent-tint-bg)" : "var(--colour-fill-quaternary)",
                  color: "var(--colour-label)",
                }}
              >
                {t.text}
              </div>
            ))}
            {busy && (
              <div className="hig-footnote" style={{ color: "var(--colour-label-tertiary)" }}>
                thinking...
              </div>
            )}
          </div>

          <form
            onSubmit={(e) => { e.preventDefault(); ask(); }}
            style={{
              display: "flex",
              gap: "var(--space-2)",
              padding: "var(--space-3)",
              borderTop: "1px solid var(--colour-separator)",
            }}
          >
            <input
              ref={inputRef}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Ask about this page..."
              style={{
                flex: 1,
                height: 32,
                padding: "0 var(--space-3)",
                border: "1px solid var(--colour-separator-opaque)",
                borderRadius: "var(--radius-sm)",
                background: "var(--colour-bg-system-secondary)",
                color: "var(--colour-label)",
                fontSize: "var(--type-callout)",
                fontFamily: "inherit",
              }}
            />
            <button
              type="submit"
              disabled={busy || !q.trim()}
              style={{
                height: 32,
                padding: "0 var(--space-3)",
                background: "var(--colour-accent)",
                color: "#FFFFFF",
                border: "none",
                borderRadius: "var(--radius-sm)",
                cursor: busy || !q.trim() ? "not-allowed" : "pointer",
                fontWeight: 600,
                opacity: busy || !q.trim() ? 0.5 : 1,
              }}
            >
              Ask
            </button>
          </form>
        </div>
      )}
    </>
  );
}
