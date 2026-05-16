import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Card, SectionEyebrow } from "../components/Card";
import { BandBar } from "../components/BandBar";

type Team = {
  team_id: number;
  name: string;
  organisation: string | null;
  role_label: string | null;
  region: string | null;
  country: string | null;
  company_id: number | null;
  company_name: string | null;
  n_respondents: number;
  avg_score_100: number;
  elite_count: number;
  at_risk_count: number;
  modal_band: string | null;
  band_elite: number;
  band_performing: number;
  band_practising: number;
  band_developing: number;
};

const AU_REGIONS = ["NSW","VIC","QLD","WA","SA","TAS","ACT","NT","Overseas"];

export default function Teams() {
  const [teams, setTeams] = useState<Team[] | null>(null);
  const [region, setRegion] = useState<string>("");
  useEffect(() => {
    api<{ teams: Team[] }>("/api/teams").then((d) => setTeams(d.teams));
  }, []);

  const filtered = (teams ?? []).filter((t) => !region || t.region === region);

  // HIG Layout: "Group related items". Group by company.
  const groups = filtered.reduce<Record<string, { id: number | null; teams: Team[] }>>((acc, t) => {
    const key = t.company_name ?? "(unassigned)";
    (acc[key] ??= { id: t.company_id, teams: [] }).teams.push(t);
    return acc;
  }, {});

  // Region tallies for the filter pill row
  const regionCounts: Record<string, number> = {};
  (teams ?? []).forEach(t => {
    const r = t.region ?? "-";
    regionCounts[r] = (regionCounts[r] ?? 0) + 1;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      <header>
        <h1 className="hig-large-title" style={{ margin: 0 }}>Teams</h1>
        <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-2)" }}>
          Every team Steve runs, nested under its parent company. Region is a filter, not part of the team name. Strict per-team scoping; zero data bleed between teams or companies.
        </p>
      </header>

      {/* Region filter pills */}
      <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap", alignItems: "center" }}>
        <span className="hig-caption-1" style={{ color: "var(--colour-label-secondary)", marginRight: "var(--space-2)" }}>Region:</span>
        <FilterPill label={`All (${teams?.length ?? 0})`} active={!region} onClick={() => setRegion("")} />
        {AU_REGIONS.filter(r => regionCounts[r]).map((r) => (
          <FilterPill key={r} label={`${r} (${regionCounts[r] ?? 0})`} active={region === r} onClick={() => setRegion(r)} />
        ))}
      </div>

      {Object.entries(groups).map(([orgName, group]) => (
        <section key={orgName} style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
          <SectionEyebrow>
            {group.id ? (
              <Link to={`/companies/${group.id}`} style={{ color: "var(--colour-accent)" }}>
                {orgName} ›
              </Link>
            ) : orgName}
          </SectionEyebrow>
          {group.teams.map((t) => (
            <Link
              key={t.team_id}
              to={`/teams/${t.team_id}`}
              style={{ textDecoration: "none", color: "inherit" }}
            >
              <Card>
                <div style={{ display: "grid", gridTemplateColumns: "1.4fr 0.7fr 0.7fr 0.7fr 1.5fr 24px", gap: "var(--space-5)", alignItems: "center" }}>
                  <div>
                    <div className="hig-headline">{t.name}</div>
                    <div className="hig-footnote">{t.role_label} Dashboard</div>
                  </div>
                  <Tile label="Reps" value={t.n_respondents} />
                  <Tile label="Avg" value={`${t.avg_score_100.toFixed(1)} /100`} />
                  <Tile label="Elite / At-risk" value={`${t.elite_count} · ${t.at_risk_count}`} />
                  <div style={{ minWidth: 0 }}>
                    <BandBar
                      label="Mix"
                      elite={t.band_elite}
                      performing={t.band_performing}
                      practising={t.band_practising}
                      developing={t.band_developing}
                    />
                  </div>
                  <span aria-hidden="true" style={{ color: "var(--colour-label-tertiary)", fontSize: "var(--type-title-3)" }}>›</span>
                </div>
              </Card>
            </Link>
          ))}
        </section>
      ))}
    </div>
  );
}

function Tile({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="hig-caption-1">{label}</div>
      <div className="hig-title-3 hig-numeric" style={{ marginTop: 2 }}>{value}</div>
    </div>
  );
}

function FilterPill({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "4px 12px",
        borderRadius: "var(--radius-pill)",
        border: "1px solid " + (active ? "var(--colour-accent)" : "var(--colour-separator-opaque)"),
        background: active ? "var(--colour-accent)" : "transparent",
        color: active ? "#FFFFFF" : "var(--colour-label)",
        fontSize: "var(--type-caption-1)",
        fontWeight: 600,
        cursor: "pointer",
        fontFamily: "inherit",
      }}
    >
      {label}
    </button>
  );
}
