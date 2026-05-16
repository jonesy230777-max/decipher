export async function api<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export type Role =
  | "admin"
  | "ceo"
  | "sales_director"
  | "hr"
  | "learning_development"
  | "sales_person";

export type Me = {
  respondent_id: number;
  email: string;
  name: string | null;
  role: Role;
};

export type Bootstrap = {
  ports: { db: string; api: string; web: string; mail: string };
  counts: {
    respondents: number;
    operators: number;
    executives: number;
    audits: number;
    audits_today: number;
    audits_month: number;
    reports: number;
    patterns_doubt_passed: number;
    industries: number;
    bespoke_clients: number;
    teams: number;
    companies: number;
    events_24h: number;
  };
  pipeline_aud: number;
  archetype_taxonomy_active: { taxonomy_id: number; name: string } | null;
  me: Me | null;
  sparks: {
    audits: number[];
    reports: number[];
    respondents: number[];
    events: number[];
    companies: number[];
    teams: number[];
    pipeline: number[];
  };
  roles: { code: Role; label: string }[];
  served_at: string;
};

export const ROLE_LABEL: Record<Role, string> = {
  admin:                "Admin",
  ceo:                  "CEO",
  sales_director:       "Sales Director",
  hr:                   "HR",
  learning_development: "Learning & Development",
  sales_person:         "Sales Person",
};
