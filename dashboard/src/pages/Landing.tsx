/**
 * Public landing / home page for Decipher. Shown when a visitor is not
 * logged in. Pitches the audit, surfaces a CTA to take the audit, and a
 * second CTA to sign in (for facilitators / directors).
 */
import { Link } from "react-router-dom";
import { Logo } from "../components/Logo";

export default function Landing() {
  return (
    <div style={{
      minHeight: "100vh",
      display: "flex", flexDirection: "column",
      background: "var(--colour-bg-system)",
      color: "var(--colour-label)",
    }}>
      {/* Top nav */}
      <header style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "var(--space-4) var(--space-7)",
        borderBottom: "1px solid var(--colour-separator)",
        background: "var(--colour-toolbar-bg)",
        backdropFilter: "saturate(180%) blur(20px)",
      }}>
        <Logo height={40} />
        <nav style={{ display: "flex", gap: "var(--space-3)", alignItems: "center" }}>
          <Link to="/login"
            style={{ color: "var(--colour-label-secondary)",
              textDecoration: "none", fontWeight: 600 }}>
            Sign in
          </Link>
          <Link to="/audit/start"
            style={{ background: "var(--colour-accent)", color: "#FFFFFF",
              padding: "10px 18px", borderRadius: "var(--radius-sm)",
              textDecoration: "none", fontWeight: 600 }}>
            Take the audit
          </Link>
        </nav>
      </header>

      {/* Hero */}
      <section style={{
        flex: 1,
             display: "grid", gridTemplateColumns: "1fr", gap: "var(--space-7)",
        padding: "var(--space-7) var(--space-7)", maxWidth: 1400, margin: "0 auto",
        alignItems: "center",
      }}>
        <div>
                    <h1 className="hig-large-title" style={{ fontSize: 56, lineHeight: 1.05,
            margin: "var(--space-3) 0 var(--space-3) 0" }}>
            The Decipher DNA Audit. <br/>
            Not a test. A clear picture of your strengths, and what to develop to close more and earn more.
          </h1>
          <div style={{ display: "flex", gap: "var(--space-3)",
            marginTop: "var(--space-5)" }}>
            <Link to="/audit/start"
              style={{ background: "var(--colour-accent)", color: "#FFFFFF",
                padding: "14px 22px", borderRadius: "var(--radius-md)",
                textDecoration: "none", fontWeight: 700, fontSize: 17 }}>
              Take the audit →
            </Link>
            <Link to="/login"
              style={{ background: "transparent",
                border: "1px solid var(--colour-separator-opaque)",
                color: "var(--colour-label)",
                padding: "14px 22px", borderRadius: "var(--radius-md)",
                textDecoration: "none", fontWeight: 600, fontSize: 17 }}>
              Client sign-in
            </Link>
          </div>
        </div>
</section>

      <footer style={{
        borderTop: "1px solid var(--colour-separator)",
        padding: "var(--space-4) var(--space-7)", textAlign: "center",
      }} className="hig-footnote">
        deciphersales.com.au · Made in Sydney · © Decipher 2026
      </footer>
    </div>
  );
}
