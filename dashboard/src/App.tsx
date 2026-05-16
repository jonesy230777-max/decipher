import { NavLink, Route, Routes } from "react-router-dom";
import { useEffect, useState } from "react";
import { api, ROLE_LABEL, type Bootstrap } from "./api";
import { Sparkline } from "./components/Sparkline";
import { GlobalSearch } from "./components/GlobalSearch";
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

type NavGroup = { heading: string; items: { path: string; label: string }[] };

const NAV: NavGroup[] = [
  {
    heading: "Overview",
    items: [
      { path: "/",       label: "Mission Control" },
      { path: "/audits", label: "Audits" },
      { path: "/cohort", label: "Cohort Insights" },
      { path: "/events", label: "Events" },
    ],
  },
  {
    heading: "Audiences",
    items: [
      { path: "/teams",      label: "Teams" },
      { path: "/industries", label: "Industries" },
      { path: "/bespoke",    label: "Bespoke" },
    ],
  },
  {
    heading: "Commerce",
    items: [
      { path: "/promo",       label: "Promo Codes" },
      { path: "/squarespace", label: "Squarespace Export" },
    ],
  },
  {
    heading: "System",
    items: [
      { path: "/settings", label: "Settings" },
    ],
  },
];

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
        flexDirection: "column",
        gap: 2,
        minWidth: 88,
      }}
    >
      <span style={{ display: "inline-flex", alignItems: "baseline", gap: "var(--space-1)" }}>
        <span style={{ color: "var(--colour-label-tertiary)" }} className="hig-caption-1">
          {label}
        </span>
        <strong className="hig-numeric" style={{ color: "var(--colour-label)" }}>
          {value ?? "·"}
        </strong>
      </span>
      {spark && spark.length > 1 && (
        <Sparkline data={spark} width={88} height={16} colour={accent ?? "var(--colour-accent)"} />
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
        display: "flex",
        alignItems: "center",
        gap: "var(--space-5)",
        padding: "var(--space-3) var(--space-5)",
        background: "var(--colour-toolbar-bg)",
        backdropFilter: "saturate(180%) blur(20px)",
        WebkitBackdropFilter: "saturate(180%) blur(20px)",
        borderBottom: "1px solid var(--colour-separator)",
        flexWrap: "wrap",
      }}
    >
      <span className="hig-headline" style={{ color: "var(--colour-label)", letterSpacing: "-0.01em" }}>
        Decipher
      </span>

      <GlobalSearch />

      <MetricChip
        label="audits today"
        value={boot?.counts.audits_today}
        spark={boot?.sparks.audits}
        accent="var(--colour-system-blue)"
      />
      <MetricChip
        label="this month"
        value={boot?.counts.audits_month}
        spark={boot?.sparks.audits}
        accent="var(--colour-system-indigo)"
      />
      <MetricChip
        label="respondents"
        value={boot?.counts.respondents}
        spark={boot?.sparks.respondents}
        accent="var(--colour-system-green)"
      />
      <MetricChip
        label="reports"
        value={boot?.counts.reports}
        spark={boot?.sparks.reports}
        accent="var(--colour-system-mint)"
      />
      <MetricChip
        label="events 24h"
        value={boot?.counts.events_24h}
        spark={boot?.sparks.events}
        accent="var(--colour-system-orange)"
      />
      <MetricChip
        label="teams"
        value={boot?.counts.teams}
      />
      <MetricChip
        label="pipeline"
        value={
          boot?.pipeline_aud != null
            ? `AUD $${Math.round(boot.pipeline_aud).toLocaleString("en-AU")}`
            : "·"
        }
      />

      {boot?.me && (
        <span
          title={`Signed in as ${boot.me.name ?? boot.me.email}`}
          style={{
            marginLeft: "auto",
            display: "inline-flex",
            alignItems: "center",
            gap: "var(--space-2)",
            padding: "4px 10px",
            minHeight: 28,
            background: "var(--colour-accent-tint-bg)",
            color: "var(--colour-accent)",
            border: "1px solid transparent",
            borderRadius: "var(--radius-sm)",
          }}
          className="hig-footnote"
        >
          <span
            aria-hidden="true"
            style={{
              width: 22, height: 22, borderRadius: "50%",
              background: "var(--colour-accent)", color: "#FFFFFF",
              display: "inline-flex", alignItems: "center", justifyContent: "center",
              fontWeight: 700, fontSize: 11,
            }}
          >
            {(boot.me.name ?? boot.me.email).slice(0, 1).toUpperCase()}
          </span>
          <span>
            <strong style={{ color: "var(--colour-accent)" }}>{boot.me.name ?? boot.me.email}</strong>
            <span style={{ color: "var(--colour-label-secondary)" }}> · {ROLE_LABEL[boot.me.role]}</span>
          </span>
        </span>
      )}
    </div>
  );
}

function Sidebar() {
  return (
    <aside
      style={{
        width: "var(--sidebar-width)",
        flexShrink: 0,
        borderRight: "1px solid var(--colour-separator-opaque)",
        background: "var(--colour-bg-system-secondary)",
        padding: "var(--space-5) var(--space-3)",
        overflowY: "auto",
      }}
    >
      {NAV.map((g) => (
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
    </aside>
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
    return () => { alive = false; clearInterval(id); };
  }, []);

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <Toolbar boot={boot} />
      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
        <Sidebar />
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
              <Route path="/"             element={<MissionControl boot={boot} />} />
              <Route path="/audits"       element={<Audits />} />
              <Route path="/cohort"       element={<CohortInsights />} />
              <Route path="/teams"        element={<Teams />} />
              <Route path="/teams/:teamId" element={<TeamExecutive />} />
              <Route path="/industries"   element={<Industries />} />
              <Route path="/bespoke"      element={<Bespoke />} />
              <Route path="/promo"        element={<PromoCodes />} />
              <Route path="/squarespace"  element={<SquarespaceExport />} />
              <Route path="/events"       element={<EventsLog />} />
              <Route path="/settings"     element={<Settings boot={boot} />} />
            </Routes>
          </main>
        </div>
      </div>
    </div>
  );
}
