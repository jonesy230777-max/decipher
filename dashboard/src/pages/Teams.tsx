import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

type Team = {
  team_id: number;
  name: string;
  organisation: string | null;
  role_label: string | null;
  n_respondents: number;
};

export default function Teams() {
  const [teams, setTeams] = useState<Team[] | null>(null);
  useEffect(() => {
    api<{ teams: Team[] }>("/api/teams").then((d) => setTeams(d.teams));
  }, []);
  return (
    <div style={{ maxWidth: 1100 }}>
      <h1 className="hig-large-title" style={{ margin: 0 }}>Teams</h1>
      <p className="hig-body" style={{ color: "var(--colour-label-secondary)", marginTop: "var(--space-2)" }}>
        Executive teams Steve manages. Click in to view as the sales director sees it.
      </p>

      <ul
        style={{
          marginTop: "var(--space-5)",
          listStyle: "none",
          padding: 0,
          background: "var(--colour-bg-system-secondary)",
          border: "1px solid var(--colour-separator-opaque)",
          borderRadius: "var(--radius-lg)",
          overflow: "hidden",
        }}
      >
        {teams?.map((t, i) => (
          <li
            key={t.team_id}
            style={{
              borderTop: i === 0 ? "none" : "1px solid var(--colour-separator)",
            }}
          >
            <Link
              to={`/teams/${t.team_id}`}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "var(--space-4)",
                padding: "var(--space-4) var(--space-5)",
                color: "var(--colour-label)",
                textDecoration: "none",
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="hig-headline">{t.name}</div>
                <div className="hig-footnote">{t.organisation} · {t.role_label} Dashboard</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div className="hig-title-3 hig-numeric">{t.n_respondents}</div>
                <div className="hig-caption-1">respondents</div>
              </div>
              <span
                aria-hidden="true"
                style={{
                  color: "var(--colour-label-tertiary)",
                  fontSize: "var(--type-title-3)",
                  lineHeight: 1,
                }}
              >
                ›
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
