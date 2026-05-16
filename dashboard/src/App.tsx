import { NavLink, Route, Routes } from "react-router-dom";
import { useEffect, useState } from "react";
import { api, type Bootstrap } from "./api";
import MissionControl from "./pages/MissionControl";
import Audits from "./pages/Audits";
import CohortInsights from "./pages/CohortInsights";
import Teams from "./pages/Teams";
import TeamExecutive from "./pages/TeamExecutive";
import Industries from "./pages/Industries";
import Bespoke from "./pages/Bespoke";
import PromoCodes from "./pages/PromoCodes";
import SquarespaceExport from "./pages/SquarespaceExport";
import EventsLog from "./pages/EventsLog";
import Settings from "./pages/Settings";

const PAGES: { path: string; label: string }[] = [
  { path: "/", label: "Mission Control" },
  { path: "/audits", label: "Audits" },
  { path: "/cohort", label: "Cohort Insights" },
  { path: "/teams", label: "Teams" },
  { path: "/industries", label: "Industries" },
  { path: "/bespoke", label: "Bespoke" },
  { path: "/promo", label: "Promo Codes" },
  { path: "/squarespace", label: "Squarespace Export" },
  { path: "/events", label: "Events" },
  { path: "/settings", label: "Settings" },
];

function HeaderStrip({ boot }: { boot: Bootstrap | null }) {
  const pipe = boot?.pipeline_aud != null
    ? `AUD $${Math.round(boot.pipeline_aud).toLocaleString("en-AU")}`
    : "-";
  return (
    <div
      style={{
        padding: "var(--space-3) var(--space-5)",
        borderBottom: "1px solid var(--colour-border-subtle)",
        background: "var(--colour-bg-elevated)",
        fontSize: "var(--type-footnote)",
        color: "var(--colour-text-secondary)",
        display: "flex",
        gap: "var(--space-5)",
        flexWrap: "wrap",
        alignItems: "center",
      }}
    >
      <span
        style={{
          fontSize: "var(--type-headline)",
          fontWeight: 700,
          color: "var(--colour-text-primary)",
          letterSpacing: "-0.01em",
        }}
      >
        Decipher
      </span>
      <span>audits today {boot?.counts.audits_today ?? "-"}</span>
      <span>this month {boot?.counts.audits_month ?? "-"}</span>
      <span>respondents {boot?.counts.respondents ?? "-"}</span>
      <span>teams {boot?.counts.teams ?? "-"}</span>
      <span>patterns {boot?.counts.patterns_doubt_passed ?? "-"}</span>
      <span>pipeline {pipe}</span>
      <span style={{ marginLeft: "auto" }}>
        ports DB {boot?.ports.db ?? "-"} · API {boot?.ports.api ?? "-"} · WEB {boot?.ports.web ?? "-"} · MAIL {boot?.ports.mail ?? "-"}
      </span>
    </div>
  );
}

function Nav() {
  return (
    <nav
      style={{
        display: "flex",
        gap: "var(--space-1)",
        padding: "var(--space-2) var(--space-5)",
        borderBottom: "1px solid var(--colour-border-subtle)",
        background: "var(--colour-bg-base)",
        overflowX: "auto",
      }}
    >
      {PAGES.map((p) => (
        <NavLink
          key={p.path}
          to={p.path}
          end={p.path === "/"}
          style={({ isActive }) => ({
            padding: "var(--space-2) var(--space-4)",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--type-callout)",
            color: isActive ? "var(--colour-text-primary)" : "var(--colour-text-secondary)",
            background: isActive ? "var(--colour-fill-secondary)" : "transparent",
            whiteSpace: "nowrap",
            textDecoration: "none",
          })}
        >
          {p.label}
        </NavLink>
      ))}
    </nav>
  );
}

export default function App() {
  const [boot, setBoot] = useState<Bootstrap | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const data = await api<Bootstrap>("/api/bootstrap");
        if (alive) {
          setBoot(data);
          setErr(null);
        }
      } catch (e) {
        if (alive) setErr(String(e));
      }
    };
    tick();
    const id = setInterval(tick, 15_000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <HeaderStrip boot={boot} />
      <Nav />
      {err && (
        <div
          role="alert"
          style={{
            padding: "var(--space-3) var(--space-5)",
            background: "var(--colour-band-developing)",
            color: "#fff",
            fontSize: "var(--type-footnote)",
          }}
        >
          API error: {err}
        </div>
      )}
      <main style={{ flex: 1, overflow: "auto", padding: "var(--space-5)" }}>
        <Routes>
          <Route path="/" element={<MissionControl boot={boot} />} />
          <Route path="/audits" element={<Audits />} />
          <Route path="/cohort" element={<CohortInsights />} />
          <Route path="/teams" element={<Teams />} />
          <Route path="/teams/:teamId" element={<TeamExecutive />} />
          <Route path="/industries" element={<Industries />} />
          <Route path="/bespoke" element={<Bespoke />} />
          <Route path="/promo" element={<PromoCodes />} />
          <Route path="/squarespace" element={<SquarespaceExport />} />
          <Route path="/events" element={<EventsLog />} />
          <Route path="/settings" element={<Settings boot={boot} />} />
        </Routes>
      </main>
    </div>
  );
}
