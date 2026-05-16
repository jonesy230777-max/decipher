import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { Logo } from "../components/Logo";
import { api } from "../api";

type Cred = { role: string; email: string; password: string };

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [creds, setCreds] = useState<Cred[]>([]);

  useEffect(() => {
    api<{ credentials: Cred[] }>("/api/auth/demo-credentials")
      .then((d) => setCreds(d.credentials)).catch(() => {});
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(null);
    try {
      await login(email.trim(), password);
      nav("/", { replace: true });
    } catch (ex: any) {
      setErr(String(ex.message ?? ex));
    } finally { setBusy(false); }
  }

  function quickFill(c: Cred) {
    setEmail(c.email); setPassword(c.password);
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex",
                  background: "var(--colour-bg-system)" }}>
      <div style={{ flex: 1, display: "flex", alignItems: "center",
                    justifyContent: "center", padding: "var(--space-7)" }}>
        <div style={{ width: "100%", maxWidth: 380 }}>
          <Link to="/" style={{ display: "inline-block",
                                marginBottom: "var(--space-5)" }}>
            <Logo height={36} />
          </Link>
          <h1 className="hig-large-title" style={{ margin: 0 }}>Sign in</h1>
          <p className="hig-callout" style={{ color: "var(--colour-label-secondary)",
                                              marginTop: "var(--space-2)" }}>
            Facilitator / director / admin access. Respondents take the audit
            from the link in their invite email.
          </p>

          <form onSubmit={submit}
                style={{ marginTop: "var(--space-5)", display: "flex",
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
                    style={{ background: "var(--colour-accent)", color: "#FFFFFF",
                             padding: "12px 16px", border: "none",
                             borderRadius: "var(--radius-md)", fontWeight: 700,
                             fontSize: "var(--type-callout)", cursor: "pointer",
                             marginTop: "var(--space-2)" }}>
              {busy ? "Signing in..." : "Sign in →"}
            </button>
          </form>
        </div>
      </div>

      <aside style={{ width: 420, padding: "var(--space-7)",
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
      </aside>
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
