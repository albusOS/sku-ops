/**
 * Auth context — supports two modes:
 *
 * 1. Supabase mode (production + any env with VITE_SUPABASE_URL set):
 *    - Login/logout via supabase.auth.*
 *    - Session managed by Supabase SDK (auto-refresh, localStorage)
 *    - Token extracted from Supabase session, attached to axios
 *    - /api/auth/me called on session change to hydrate enriched profile
 *
 * 2. Bridge mode (dev without Supabase credentials):
 *    - Login via POST /api/auth/login (local users table, bcrypt)
 *    - Token stored in sessionStorage
 *    - /api/auth/me called on load to restore session
 *
 * The rest of the app is identical in both modes — it reads from `user` and
 * calls `login(email, password)` / `logout()` regardless of which mode is active.
 */

import { createContext, useContext, useState, useEffect, useRef } from "react";
import axios from "axios";
import api from "@/lib/api-client";
import { isSupabaseConfigured, getSupabase } from "@/lib/supabase";

const AuthContext = createContext(null);

const isAuthEndpoint = (url) => {
  if (!url) return false;
  return url.includes("/auth/login") || url.includes("/auth/register");
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const logoutRef = useRef(null);

  // ── Shared helpers ──────────────────────────────────────────────────────────

  const _setAxiosToken = (t) => {
    if (t) {
      axios.defaults.headers.common["Authorization"] = `Bearer ${t}`;
    } else {
      delete axios.defaults.headers.common["Authorization"];
    }
    setToken(t || null);
  };

  const _fetchProfile = async () => {
    try {
      const data = await api.auth.me();
      setUser(data);
      return data;
    } catch {
      logoutRef.current?.();
      return null;
    }
  };

  // ── 401 interceptor (shared) ────────────────────────────────────────────────

  useEffect(() => {
    logoutRef.current = isSupabaseConfigured ? _supabaseLogout : _bridgeLogout;
  });

  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      (res) => res,
      (error) => {
        if (error.response?.status === 401 && !isAuthEndpoint(error.config?.url)) {
          logoutRef.current?.();
        }
        return Promise.reject(error);
      },
    );
    return () => axios.interceptors.response.eject(interceptor);
  }, []);

  // ── Supabase mode ───────────────────────────────────────────────────────────

  const _supabaseLogout = async () => {
    const sb = await getSupabase();
    await sb.auth.signOut();
    _setAxiosToken(null);
    setUser(null);
  };

  useEffect(() => {
    if (!isSupabaseConfigured) return;

    let subscription;
    getSupabase().then((sb) => {
      const {
        data: { subscription: sub },
      } = sb.auth.onAuthStateChange(async (_event, session) => {
        if (session?.access_token) {
          _setAxiosToken(session.access_token);
          await _fetchProfile();
        } else {
          _setAxiosToken(null);
          setUser(null);
          setLoading(false);
        }
      });
      subscription = sub;

      // Hydrate on mount from existing session
      sb.auth.getSession().then(({ data: { session } }) => {
        if (session?.access_token) {
          _setAxiosToken(session.access_token);
          _fetchProfile().finally(() => setLoading(false));
        } else {
          setLoading(false);
        }
      });
    });

    return () => subscription?.unsubscribe();
  }, []);

  const _supabaseLogin = async (email, password) => {
    const sb = await getSupabase();
    const { data, error } = await sb.auth.signInWithPassword({ email, password });
    if (error) throw error;
    _setAxiosToken(data.session.access_token);
    const profile = await _fetchProfile();
    return profile;
  };

  const _supabaseRegister = async (email, password, name) => {
    const sb = await getSupabase();
    const { data, error } = await sb.auth.signUp({
      email,
      password,
      options: { data: { name } },
    });
    if (error) throw error;
    if (data.session?.access_token) {
      _setAxiosToken(data.session.access_token);
      await _fetchProfile();
    }
    return user;
  };

  // ── Bridge mode (dev, no Supabase) ──────────────────────────────────────────

  const refreshTimerRef = useRef(null);
  const scheduleBridgeRefreshRef = useRef(null);

  scheduleBridgeRefreshRef.current = (jwt) => {
    clearTimeout(refreshTimerRef.current);
    try {
      const payload = JSON.parse(atob(jwt.split(".")[1]));
      const expiresAt = payload.exp * 1000;
      // Refresh 2 minutes before expiry, minimum 30 seconds from now
      const refreshAt = Math.max(expiresAt - 2 * 60 * 1000, Date.now() + 30_000);
      const delay = refreshAt - Date.now();
      refreshTimerRef.current = setTimeout(async () => {
        try {
          const { token: newJwt } = await api.auth.refresh();
          sessionStorage.setItem("token", newJwt);
          _setAxiosToken(newJwt);
          scheduleBridgeRefreshRef.current?.(newJwt);
        } catch {
          logoutRef.current?.();
        }
      }, delay);
    } catch {
      /* malformed token — will fail on next API call and trigger logout */
    }
  };

  const _bridgeLogout = () => {
    clearTimeout(refreshTimerRef.current);
    sessionStorage.removeItem("token");
    _setAxiosToken(null);
    setUser(null);
  };

  useEffect(() => {
    if (isSupabaseConfigured) return;

    const saved = sessionStorage.getItem("token");
    if (saved) {
      _setAxiosToken(saved);
      scheduleBridgeRefreshRef.current?.(saved);
      _fetchProfile().finally(() => setLoading(false));
    } else {
      setLoading(false);
    }

    return () => clearTimeout(refreshTimerRef.current);
  }, []);

  const _bridgeLogin = async (email, password) => {
    const { token: jwt, user: userData } = await api.auth.login({ email, password });
    sessionStorage.setItem("token", jwt);
    _setAxiosToken(jwt);
    scheduleBridgeRefreshRef.current?.(jwt);
    setUser(userData);
    return userData;
  };

  const _bridgeRegister = async (email, password, name) => {
    const { token: jwt, user: userData } = await api.auth.register({ email, password, name });
    sessionStorage.setItem("token", jwt);
    _setAxiosToken(jwt);
    scheduleBridgeRefreshRef.current?.(jwt);
    setUser(userData);
    return userData;
  };

  // ── Public API ──────────────────────────────────────────────────────────────

  const login = isSupabaseConfigured ? _supabaseLogin : _bridgeLogin;
  const register = isSupabaseConfigured ? _supabaseRegister : _bridgeRegister;
  const logout = () => {
    if (isSupabaseConfigured) {
      _supabaseLogout();
    } else {
      _bridgeLogout();
    }
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};
