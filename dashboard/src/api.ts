export async function api<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export type Bootstrap = {
  ports: { db: string; api: string; web: string; mail: string };
  counts: {
    respondents: number;
    operators: number;
    audits: number;
    audits_today: number;
    audits_month: number;
    reports: number;
    patterns_doubt_passed: number;
    industries: number;
    bespoke_clients: number;
    events_24h: number;
  };
  archetype_taxonomy_active: { taxonomy_id: number; name: string } | null;
  served_at: string;
};
