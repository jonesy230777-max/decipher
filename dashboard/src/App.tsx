import { NavLink, Route, Routes, useLocation, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { api, ROLE_LABEL, type Bootstrap, type Role } from "./api";
import { useAuth, type AuthMe } from "./auth";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import MyProfile from "./pages/MyProfile";
import { Sparkline } from "./components/Sparkline";
import { GlobalSearch } from "./components/GlobalSearch";
import { Logo } from "./components/Logo";
import { AiAssistant } from "./components/AiAssistant";
import MissionControl from "./pages/MissionControl";
import Audits from "./pages/Audits";
import CohortInsights from "./pages/CohortInsights";
import Teams from "./pages/Teams";
import TeamExecutive from "./pages/TeamExecutive";
import Companies from "./pages/Companies";
import CompanyDetail from "./pages/CompanyDetail";
import RespondentDetail from "./pages/RespondentDetail";
import AuditTake from "./pages/AuditTake";
import Funnel from "./pages/Funnel";
import People from "./pages/People";
import Industries from "./pages/Industries";
import Bespoke from "./pages/Bespoke";
import PromoCodes from "./pages/PromoCodes";
import EventsLog from "./pages/EventsLog";
import Settings from "./pages/Settings";

type NavGroup = { heading: string; items: { path: string; label: string }[] };

const _ALL_NAV: NavGroup[] = [
  {
    heading: "Overview",
    items: [
      { path: "/",       label: "Mission Control" },
      { path: "/funnel", label: "Funnel" },
      { path: "/audits", label: "Audits" },
      { path: "/cohort", label: "Cohort Insights" },
      { path: "/events", label: "Events" },
    ],
  },
  {
    heading: "Audiences",
    items: [
      { path: "/companies",  label: "Companies" },
      { path: "/teams",      label: "Teams" },
      { path: "/people",     label: "People" },
      { path: "/industries", label: "Industries" },
      { path: "/bespoke",    label: "Bespoke" },
    ],
  },
  {
    heading: "Commerce",
    items: [
      { path: "/promo",       label: "Promo Codes" },
    ],
  },
  {
    heading: "System",
    items: [
      { path: "/settings", label: "Settings" },
    ],
  },
];

// Paths permitted per role. admin = all. sales_person = own profile only.
const _ROLE_PATHS: Partial<Record<Role, Set<string>>> = {
  ceo:                  new Set(["/", "/funnel", "/audits", "/cohort", "/events", "/companies", "/teams", "/people"]),
  sales_director:       new Set(["/", "/audits", "/cohort", "/teams", "/people"]),
  hr:                   new Set(["/people", "/companies", "/cohort", "/teams"]),
  learning_development: new Set(["/", "/audits", "/cohort", "/teams", "/people"]),
  sales_person:         new Set(["/me"]),
};

function _navForRole(role: Role): NavGroup[] {
  if (role === "admin") return _ALL_NAV;
  if (role === "sales_person") return [{ heading: "My Profile", items: [{ path: "/me", label: "My Profile" }] }];
  const allowed = _ROLE_PATHS[role];
  if (!allowed) return _ALL_NAV;
  return _ALL_NAV.map((g) => ({
    ...g,
    items: g.items.filter((it) => allowed.has(it.path)),
  })).filter((g) => g.items.length > 0);
}

function MetricChip({
  label, value, spark, accent,
}: {
  label: string;
  value: string | number | undefined;
  spark?: number[];
  accent?: string;
}) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        minHeight: 24,
        flexShrink: 0,
        whiteSpace: "nowrap",
      }}
    >
      <span
        style={{
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: "-0.005em",
          color: "var(--colour-label-secondary)",
        }}
      >
        {label}
      </span>
      <strong
        className="hig-numeric"
        style={{ color: "var(--colour-label)", textAlign: "right", fontSize: 13 }}
      >
        {value ?? "·"}
      </strong>
      {spark && spark.length > 1 && (
        <Sparkline data={spark} width={40} height={12} colour={accent ?? "var(--colour-accent)"} />
      )}
    </span>
  );
}

function Toolbar({ boot }: { boot: Bootstrap | null }) {
  return (
    <div
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        background: "var(--colour-toolbar-bg)",
        backdropFilter: "saturate(180%) blur(20px)",
        WebkitBackdropFilter: "saturate(180%) blur(20px)",
        borderBottom: "1px solid var(--colour-separator)",
      }}
    >
      {/* Row 1: brand + metrics (single-line, no wrap, scales to viewport) */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "var(--space-4)",
          padding: "var(--space-3) var(--space-4)",
          flexWrap: "nowrap",
          overflow: "hidden",
        }}
      >
        <div style={{ flexShrink: 0 }}>
          <Logo height={36} />
        </div>
        <div style={{
          display: "flex", flex: 1, minWidth: 0, gap: "var(--space-3)",
          alignItems: "center", flexWrap: "nowrap", overflow: "hidden",
          justifyContent: "flex-end",
        }}>
          <MetricChip label="Audits Today" value={boot?.counts.audits_today} spark={boot?.sparks.audits}      accent="var(--colour-system-blue)" />
          <MetricChip label="This Month"   value={boot?.counts.audits_month} spark={boot?.sparks.audits}      accent="var(--colour-system-indigo)" />
          <MetricChip label="Respondents"  value={boot?.counts.respondents}  spark={boot?.sparks.respondents} accent="var(--colour-system-green)" />
          <MetricChip label="Reports"      value={boot?.counts.reports}      spark={boot?.sparks.reports}     accent="var(--colour-system-mint)" />
          <MetricChip label="Events 24h"   value={boot?.counts.events_24h}   spark={boot?.sparks.events}      accent="var(--colour-system-orange)" />
          <MetricChip label="Teams"        value={boot?.counts.teams}              spark={boot?.sparks.teams}     accent="var(--colour-system-purple)" />
          <MetricChip label="Companies"    value={boot?.counts.companies ?? "·"}   spark={boot?.sparks.companies} accent="var(--colour-system-teal)" />
          <MetricChip
            label="Pipeline"
            value={
              boot?.pipeline_aud != null
                ? `$${Math.round(boot.pipeline_aud / 1000)}k`
                : "·"
            }
            spark={boot?.sparks.pipeline}
            accent="var(--colour-system-pink)"
          />
        </div>
      </div>

      {/* Row 2: centered search */}
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          padding: "var(--space-2) var(--space-5) var(--space-3)",
          borderTop: "1px solid var(--colour-separator)",
        }}
      >
        <div style={{ width: "100%", maxWidth: 640 }}>
          <GlobalSearch />
        </div>
      </div>
    </div>
  );
}

function Sidebar({ boot }: { boot: Bootstrap | null }) {
  const { me, logout } = useAuth();
  const display = me ?? boot?.me ?? null;
  const nav = display ? _navForRole(display.role) : _ALL_NAV;
  return (
    <aside
      style={{
        width: "var(--sidebar-width)",
        flexShrink: 0,
        borderRight: "1px solid var(--colour-separator-opaque)",
        background: "var(--colour-bg-system-secondary)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div style={{ flex: 1, overflowY: "auto", padding: "var(--space-5) var(--space-3)" }}>
        {nav.map((g) => (
          <div key={g.heading} style={{ marginBottom: "var(--space-5)" }}>
            <div
              className="hig-caption-1"
              style={{
                padding: "var(--space-2) var(--space-3)",
                color: "var(--colour-label-tertiary)",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              {g.heading}
            </div>
            {g.items.map((it) => (
              <NavLink
                key={it.path}
                to={it.path}
                end={it.path === "/"}
                style={({ isActive }) => ({
                  display: "block",
                  padding: "var(--space-2) var(--space-3)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "var(--type-callout)",
                  lineHeight: "var(--lead-callout)",
                  color: isActive ? "#FFFFFF" : "var(--colour-label)",
                  background: isActive ? "var(--colour-accent)" : "transparent",
                  fontWeight: isActive ? 600 : 400,
                  marginBottom: 2,
                  textDecoration: "none",
                })}
              >
                {it.label}
              </NavLink>
            ))}
          </div>
        ))}
      </div>

      {/* Signed-in user — bottom-left of the sidebar */}
      {display && (
        <div
          style={{
            borderTop: "1px solid var(--colour-separator-opaque)",
            padding: "var(--space-3)",
            display: "flex",
            alignItems: "center",
            gap: "var(--space-3)",
            background: "var(--colour-bg-system-secondary)",
          }}
        >
          <span
            aria-hidden="true"
            style={{
              width: 32, height: 32, borderRadius: "50%",
              background: "var(--colour-accent)", color: "#FFFFFF",
              display: "inline-flex", alignItems: "center", justifyContent: "center",
              fontWeight: 700, fontSize: 14,
              flexShrink: 0,
            }}
          >
            {(display.name ?? display.email).slice(0, 1).toUpperCase()}
          </span>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div className="hig-callout" style={{ fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {display.name ?? display.email}
            </div>
            <div className="hig-caption-1" style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {ROLE_LABEL[display.role]}
            </div>
          </div>
          <button
            onClick={logout}
            title="Sign out"
            aria-label="Sign out"
            style={{
              background: "transparent",
              border: "1px solid var(--colour-separator-opaque)",
              color: "var(--colour-label-secondary)",
              padding: "4px 10px", borderRadius: "var(--radius-sm)",
              fontSize: 11, fontWeight: 600, cursor: "pointer",
            }}
          >
            Sign out
          </button>
        </div>
      )}
    </aside>
  );
}

function MagicLinkConsume() {
  const [params] = useSearchParams();
  const { loginWithToken } = useAuth();
  const nav = useNavigate();
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const token = params.get("token");
    if (!token) { setErr("Missing token in URL."); return; }
    api<{ ok: boolean; token: string; me: AuthMe }>(`/api/auth/magic-link/consume?token=${encodeURIComponent(token)}`)
      .then((r) => { loginWithToken(r.token, r.me); nav("/", { replace: true }); })
      .catch((e) => setErr(String(e.message ?? e)));
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  if (err) return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center",
                  justifyContent: "center", background: "var(--colour-bg-system)" }}>
      <div style={{ maxWidth: 380, textAlign: "center" }}>
        <p className="hig-callout" style={{ color: "var(--colour-system-red)", fontWeight: 700 }}>
          Sign-in link invalid
        </p>
        <p className="hig-footnote" style={{ color: "var(--colour-label-secondary)" }}>{err}</p>
        <a href="/login" className="hig-callout"
           style={{ color: "var(--colour-accent)", textDecoration: "none" }}>
          Back to sign in
        </a>
      </div>
    </div>
  );
  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center",
                  justifyContent: "center", background: "var(--colour-bg-system)" }}>
      <p className="hig-callout" style={{ color: "var(--colour-label-secondary)" }}>
        Signing you in...
      </p>
    </div>
  );
}

export default function App() {
  const { me, loading } = useAuth();
  const loc = useLocation();
  const [boot, setBoot] = useState<Bootstrap | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!me) return;
    let alive = true;
    const tick = async () => {
      try {
        const data = await api<Bootstrap>("/api/bootstrap");
        if (alive) { setBoot(data); setErr(null); }
      } catch (e) {
        if (alive) setErr(String(e));
      }
    };
    tick();
    const id = setInterval(tick, 15_000);
    return () => { alive = false; clearInterval(id); };
  }, [me]);

  if (loading) return null;

  // Public routes (no admin chrome / no auth required).
  if (loc.pathname === "/landing")           return <Landing />;
  if (loc.pathname === "/login")             return <Login />;
  if (loc.pathname === "/auth/magic-link")   return <MagicLinkConsume />;
  if (loc.pathname.startsWith("/audit/")) {
    return (
      <Routes>
        <Route path="/audit/start"     element={<AuditTake />} />
        <Route path="/audit/:auditId"  element={<AuditTake />} />
      </Routes>
    );
  }

  // Not signed in → public landing for root; force login for everything else.
  if (!me) {
    if (loc.pathname === "/") return <Landing />;
    return <Navigate to="/login" replace />;
  }

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <Toolbar boot={boot} />
      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
        <Sidebar boot={boot} />
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
          {err && (
            <div
              role="alert"
              className="hig-footnote"
              style={{
                padding: "var(--space-3) var(--space-5)",
                background: "var(--colour-system-red)",
                color: "#FFFFFF",
              }}
            >
              API error: {err}
            </div>
          )}
          <main style={{ flex: 1, overflow: "auto", padding: "var(--space-6) var(--space-7)" }}>
            <Routes>
              <Route path="/"              element={<MissionControl boot={boot} />} />
              <Route path="/audits"        element={<Audits />} />
              <Route path="/funnel"        element={<Funnel boot={boot} />} />
              <Route path="/cohort"        element={<CohortInsights />} />
              <Route path="/companies"           element={<Companies />} />
              <Route path="/companies/:companyId" element={<CompanyDetail />} />
              <Route path="/teams"               element={<Teams />} />
              <Route path="/teams/:teamId"       element={<TeamExecutive />} />
              <Route path="/respondents/:id"     element={<RespondentDetail />} />
              <Route path="/people"              element={<People />} />
              <Route path="/audit/start"         element={<AuditTake />} />
              <Route path="/audit/:auditId"      element={<AuditTake />} />
              <Route path="/industries"    element={<Industries />} />
              <Route path="/bespoke"       element={<Bespoke />} />
              <Route path="/promo"         element={<PromoCodes />} />
              <Route path="/events"        element={<EventsLog />} />
              <Route path="/settings"      element={<Settings boot={boot} />} />
              <Route path="/me"            element={<MyProfile />} />
            </Routes>
          </main>
        </div>
      </div>
      <AiAssistant />
    </div>
  );
}
