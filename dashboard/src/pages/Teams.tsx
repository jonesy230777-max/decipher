import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Card } from "../components/Card";

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
    <div>
      <h1 style={{ fontSize: "var(--type-title-1)", fontWeight: 600, margin: 0 }}>Teams</h1>
      <p style={{ color: "var(--colour-text-secondary)", marginTop: "var(--space-2)" }}>
        Executive teams Steve manages. Click in to view as the sales director sees it.
      </p>
      <div style={{ marginTop: "var(--space-5)", display: "grid", gap: "var(--space-3)" }}>
        {teams?.map((t) => (
          <Link
            key={t.team_id}
            to={`/teams/${t.team_id}`}
            style={{ textDecoration: "none", color: "inherit" }}
          >
            <Card>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontSize: "var(--type-title-3)", fontWeight: 600 }}>{t.name}</div>
                  <div style={{ color: "var(--colour-text-secondary)", marginTop: "var(--space-1)" }}>
                    {t.organisation} · {t.role_label} Dashboard
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: "var(--type-large-title)", fontWeight: 700 }}>{t.n_respondents}</div>
                  <div style={{ color: "var(--colour-text-tertiary)", fontSize: "var(--type-footnote)" }}>
                    respondents
                  </div>
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
