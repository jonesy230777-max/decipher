import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { Logo } from "../components/Logo";
import { api } from "../api";

type Cred = { role: string; email: string; password: string };
type Tab = "password" | "magic";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [tab, setTab] = useState<Tab>("password");

  // Password tab state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [creds, setCreds] = useState<Cred[]>([]);

  // Magic-link tab state
  const [magicEmail, setMagicEmail] = useState("");
  const [magicBusy, setMagicBusy] = useState(false);
  const [magicErr, setMagicErr] = useState<string | null>(null);
  const [magicSent, setMagicSent] = useState(false);

  useEffect(() => {
    api<{ credentials: Cred[] }>("/api/auth/demo-credentials")
      .then((d) => setCreds(d.credentials)).catch(() => {});
  }, []);

  async function submitPassword(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(null);
    try {
      await login(email.trim(), password);
      nav("/", { replace: true });
    } catch (ex: any) {
      setErr(String(ex.message ?? ex));
    } finally { setBusy(false); }
  }

  async function submitMagic(e: React.FormEvent) {
    e.preventDefault();
    setMagicBusy(true); setMagicErr(null);
    try {
      await api("/api/auth/magic-link/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: magicEmail.trim() }),
      });
      setMagicSent(true);
    } catch (ex: any) {
      setMagicErr(String(ex.message ?? ex));
    } finally { setMagicBusy(false); }
  }

  function quickFill(c: Cred) {
    setTab("password");
    setEmail(c.email); setPassword(c.password);
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex",
                  background: "var(--colour-bg-system)" }}>
      <div style={{ flex: 1, display: "flex", alignItems: "center",
                    justifyContent: "center", padding: "var(--space-7)" }}>
        <div style={{ width: "100%", maxWidth: 380 }}>
          <Link to="/" style={{ display: "inline-block", marginBottom: "var(--space-5)" }}>
            <Logo height={36} />
          </Link>
          <h1 className="hig-large-title" style={{ margin: 0 }}>Sign in</h1>
          <p className="hig-callout" style={{ color: "var(--colour-label-secondary)",
                                              marginTop: "var(--space-2)" }}>
            Facilitator / director / admin access. Respondents take the audit
            from the link in their invite email.
          </p>

          {/* Tab switcher */}
          <div style={{ display: "flex", gap: 4, marginTop: "var(--space-5)",
                        background: "var(--colour-bg-system-secondary)",
                        borderRadius: "var(--radius-md)",
                        padding: 4, border: "1px solid var(--colour-separator-opaque)" }}>
            {(["password", "magic"] as Tab[]).map((t) => (
              <button key={t} onClick={() => setTab(t)}
                      style={{ flex: 1, padding: "7px 12px",
                               border: "none", borderRadius: "calc(var(--radius-md) - 2px)",
                               fontFamily: "inherit",
                               fontSize: "var(--type-footnote)", fontWeight: 600,
                               cursor: "pointer",
                               background: tab === t ? "var(--colour-bg-system)" : "transparent",
                               color: tab === t ? "var(--colour-label)" : "var(--colour-label-secondary)",
                               boxShadow: tab === t ? "0 1px 3px rgba(0,0,0,.12)" : "none" }}>
                {t === "password" ? "Password" : "Magic link"}
              </button>
            ))}
          </div>

          {tab === "password" && (
            <form onSubmit={submitPassword}
                  style={{ marginTop: "var(--space-4)", display: "flex",
                           flexDirection: "column", gap: "var(--space-3)" }}>
              <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <span className="hig-caption-1">Email</span>
                <input value={email} onChange={(e) => setEmail(e.target.value)}
                       type="email" autoComplete="username"
                       style={inputStyle} required />
              </label>
              <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <span className="hig-caption-1">Password</span>
                <input value={password} onChange={(e) => setPassword(e.target.value)}
                       type="password" autoComplete="current-password"
                       style={inputStyle} required />
              </label>
              {err && (
                <div role="alert"
                     style={{ background: "var(--colour-system-red)", color: "#FFFFFF",
                              padding: "8px 12px", borderRadius: "var(--radius-sm)",
                              fontSize: "var(--type-footnote)" }}>
                  {err}
                </div>
              )}
              <button type="submit" disabled={busy}
                      style={primaryBtn}>
                {busy ? "Signing in..." : "Sign in →"}
              </button>
            </form>
          )}

          {tab === "magic" && (
            magicSent ? (
              <div style={{ marginTop: "var(--space-5)", padding: "var(--space-5)",
                            background: "var(--colour-bg-system-secondary)",
                            borderRadius: "var(--radius-md)",
                            border: "1px solid var(--colour-separator-opaque)",
                            textAlign: "center" }}>
                <div style={{ fontSize: 32, marginBottom: "var(--space-3)" }}>✉</div>
                <p className="hig-callout" style={{ fontWeight: 600, margin: 0 }}>
                  Check your inbox
                </p>
                <p className="hig-footnote"
                   style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-2)" }}>
                  A sign-in link was sent to <strong>{magicEmail}</strong>.
                  It expires in 48 hours.
                </p>
                <button onClick={() => { setMagicSent(false); setMagicEmail(""); }}
                        style={{ marginTop: "var(--space-3)", background: "transparent",
                                 border: "none", color: "var(--colour-accent)",
                                 cursor: "pointer", fontSize: "var(--type-footnote)" }}>
                  Send another link
                </button>
              </div>
            ) : (
              <form onSubmit={submitMagic}
                    style={{ marginTop: "var(--space-4)", display: "flex",
                             flexDirection: "column", gap: "var(--space-3)" }}>
                <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <span className="hig-caption-1">Email</span>
                  <input value={magicEmail} onChange={(e) => setMagicEmail(e.target.value)}
                         type="email" autoComplete="username"
                         placeholder="your@email.com"
                         style={inputStyle} required />
                </label>
                {magicErr && (
                  <div role="alert"
                       style={{ background: "var(--colour-system-red)", color: "#FFFFFF",
                                padding: "8px 12px", borderRadius: "var(--radius-sm)",
                                fontSize: "var(--type-footnote)" }}>
                    {magicErr}
                  </div>
                )}
                <button type="submit" disabled={magicBusy} style={primaryBtn}>
                  {magicBusy ? "Sending..." : "Send sign-in link →"}
                </button>
                <p className="hig-footnote"
                   style={{ color: "var(--colour-label-tertiary)", textAlign: "center", margin: 0 }}>
                  We'll email a one-time link. No password needed.
                </p>
              </form>
            )
          )}
        </div>
      </div>

      {creds.length > 0 && (<aside style={{ width: 420, padding: "var(--space-7)",
                       borderLeft: "1px solid var(--colour-separator-opaque)",
                       background: "var(--colour-bg-system-secondary)" }}>
        <h2 className="hig-title-3" style={{ marginTop: 0 }}>Demo credentials</h2>
        <p className="hig-caption-1" style={{ color: "var(--colour-label-secondary)" }}>
          Click any row to fill the form. These accounts exist in the seed.
        </p>
        <ul style={{ listStyle: "none", padding: 0, margin: "var(--space-4) 0",
                     display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          {creds.map((c) => (
            <li key={c.email}>
              <button onClick={() => quickFill(c)}
                      style={{ width: "100%", textAlign: "left",
                               background: "var(--colour-bg-system)",
                               border: "1px solid var(--colour-separator-opaque)",
                               borderRadius: "var(--radius-md)",
                               padding: "var(--space-3) var(--space-4)",
                               cursor: "pointer",
                               fontFamily: "inherit", color: "var(--colour-label)" }}>
                <div className="hig-callout" style={{ fontWeight: 700 }}>{c.role}</div>
                <div className="hig-footnote hig-numeric"
                     style={{ color: "var(--colour-label-secondary)" }}>
                  {c.email} · {c.password}
                </div>
              </button>
            </li>
          ))}
        </ul>
      </aside>)}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  height: 40,
  padding: "0 var(--space-3)",
  border: "1px solid var(--colour-separator-opaque)",
  borderRadius: "var(--radius-sm)",
  background: "var(--colour-bg-system-secondary)",
  color: "var(--colour-label)",
  fontSize: "var(--type-body)",
  fontFamily: "inherit",
};

const primaryBtn: React.CSSProperties = {
  background: "var(--colour-accent)",
  color: "#FFFFFF",
  padding: "12px 16px",
  border: "none",
  borderRadius: "var(--radius-md)",
  fontWeight: 700,
  fontSize: "var(--type-callout)",
  cursor: "pointer",
  marginTop: "var(--space-2)",
};
