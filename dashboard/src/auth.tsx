import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { api, type Role } from "./api";

export type AuthMe = {
  respondent_id: number;
  email: string;
  name: string | null;
  first_name?: string | null;
  last_name?: string | null;
  role: Role;
};

type AuthCtx = {
  me: AuthMe | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
};

const Ctx = createContext<AuthCtx>({
  me: null, login: async () => {}, logout: () => {}, loading: true,
});

const STORAGE_KEY = "decipher.me";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<AuthMe | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      try { setMe(JSON.parse(raw)); } catch { /* */ }
    }
    setLoading(false);
  }, []);

  async function login(email: string, password: string) {
    const r = await api<{ me: AuthMe }>("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(r.me));
    setMe(r.me);
  }
  function logout() {
    localStorage.removeItem(STORAGE_KEY);
    setMe(null);
  }

  return <Ctx.Provider value={{ me, login, logout, loading }}>{children}</Ctx.Provider>;
}

export function useAuth() { return useContext(Ctx); }
