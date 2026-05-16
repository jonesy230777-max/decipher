import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

type Hit = {
  kind: "respondent" | "audit" | "bespoke" | "promo" | "industry" | "team" | "pattern" | "event";
  label: string;
  sub: string;
  href: string;
};

const KIND_LABEL: Record<Hit["kind"], string> = {
  respondent: "Respondent",
  audit:      "Audit",
  bespoke:    "Bespoke",
  promo:      "Promo",
  industry:   "Industry",
  team:       "Team",
  pattern:    "Pattern",
  event:      "Event",
};

export function GlobalSearch() {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [hits, setHits] = useState<Hit[]>([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  // Cmd/Ctrl-K focuses the search field (HIG-style global keyboard shortcut).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
        setOpen(true);
      }
      if (e.key === "Escape") {
        setOpen(false);
        inputRef.current?.blur();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Click outside closes.
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  // Debounced fetch.
  useEffect(() => {
    if (!q.trim()) {
      setHits([]);
      return;
    }
    setLoading(true);
    const t = setTimeout(() => {
      api<{ hits: Hit[] }>(`/api/search?q=${encodeURIComponent(q)}`)
        .then((d) => setHits(d.hits))
        .catch(() => setHits([]))
        .finally(() => setLoading(false));
    }, 180);
    return () => clearTimeout(t);
  }, [q]);

  function submit() {
    setOpen(true);
    inputRef.current?.focus();
  }

  return (
    <div ref={wrapRef} style={{ position: "relative", width: "100%", display: "flex", gap: "var(--space-2)" }}>
      <input
        ref={inputRef}
        type="search"
        placeholder="Search audits, teams, codes…  ⌘K"
        value={q}
        onChange={(e) => { setQ(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
        style={{
          flex: 1,
          height: 36,
          padding: "0 var(--space-3)",
          border: "1px solid var(--colour-separator-opaque)",
          borderRadius: "var(--radius-sm)",
          background: "var(--colour-bg-system-secondary)",
          color: "var(--colour-label)",
          fontSize: "var(--type-callout)",
          lineHeight: "var(--lead-callout)",
          fontFamily: "inherit",
        }}
      />
      <button
        onClick={submit}
        className="hig-callout"
        style={{
          height: 36,
          padding: "0 var(--space-4)",
          background: "var(--colour-accent)",
          color: "#FFFFFF",
          border: "1px solid transparent",
          borderRadius: "var(--radius-sm)",
          cursor: "pointer",
          fontWeight: 600,
          minWidth: 88,
        }}
      >
        Search
      </button>
      {open && (q.trim().length > 0 || loading) && (
        <div
          role="listbox"
          style={{
            position: "absolute",
            top: 40,
            left: 0,
            right: 96,
            maxHeight: 360,
            overflowY: "auto",
            background: "var(--colour-bg-system)",
            border: "1px solid var(--colour-separator-opaque)",
            borderRadius: "var(--radius-md)",
            boxShadow: "var(--shadow-2)",
            zIndex: 60,
          }}
        >
          {loading && (
            <div className="hig-footnote" style={{ padding: "var(--space-3)", color: "var(--colour-label-tertiary)" }}>
              Searching...
            </div>
          )}
          {!loading && hits.length === 0 && q.trim() && (
            <div className="hig-footnote" style={{ padding: "var(--space-3)", color: "var(--colour-label-tertiary)" }}>
              No matches.
            </div>
          )}
          {hits.map((h, i) => (
            <button
              key={i}
              role="option"
              onClick={() => {
                navigate(h.href);
                setOpen(false);
                setQ("");
              }}
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                padding: "var(--space-2) var(--space-3)",
                border: "none",
                borderTop: i === 0 ? "none" : "1px solid var(--colour-separator)",
                background: "transparent",
                color: "var(--colour-label)",
                cursor: "pointer",
              }}
            >
              <div style={{ display: "flex", alignItems: "baseline", gap: "var(--space-2)" }}>
                <span
                  className="hig-caption-2"
                  style={{
                    padding: "1px 6px",
                    borderRadius: "var(--radius-pill)",
                    background: "var(--colour-fill-quaternary)",
                    color: "var(--colour-label-secondary)",
                  }}
                >
                  {KIND_LABEL[h.kind]}
                </span>
                <span className="hig-callout" style={{ flex: 1, fontWeight: 600 }}>
                  {h.label}
                </span>
              </div>
              {h.sub && (
                <div className="hig-footnote" style={{ marginLeft: 48 }}>{h.sub}</div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
