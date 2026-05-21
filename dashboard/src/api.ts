const _TOKEN_KEY = "decipher.token";

export function setToken(token: string): void {
  localStorage.setItem(_TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(_TOKEN_KEY);
}

export function getToken(): string | null {
  return localStorage.getItem(_TOKEN_KEY);
}

export async function api<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = { ...(init?.headers as Record<string, string> ?? {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(path, { ...init, headers });
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

export type DimMeans = {
  cognitive_empathy: number;
  eq: number;
  pressure_composure: number;
  storytelling: number;
  n_scored: number;
};

export type Bootstrap = {
  ports: { db: string; api: string; web: string; mail: string };
  dim_means_30d: DimMeans;
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
