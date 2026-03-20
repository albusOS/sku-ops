/** Auth context - Supabase session management plus backend profile hydration. */

import { createContext, useContext, useState, useEffect, useRef } from "react";
import axios from "axios";
import { toast } from "sonner";
import api from "@/lib/api-client";
import { getSupabase, isSupabaseConfigured } from "@/lib/supabase";

const AuthContext = createContext(null);

const isAuthEndpoint = (url) => {
  if (!url) return false;
  return false;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const logoutRef = useRef(null);

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
    } catch (err) {
      const status = err?.response?.status;
      // Only invalidate the session on explicit auth rejections.
      // Network errors, 5xx during startup/restart, etc. should not log the
      // user out — they would silently destroy a valid session.
      if (status === 401 || status === 403) {
        toast.error("Session expired — please log in again.");
        logoutRef.current?.();
      }
      return null;
    }
  };

  useEffect(() => {
    logoutRef.current = _supabaseLogout;
  });

  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      (res) => res,
      (error) => {
        if (error.response?.status === 401 && !isAuthEndpoint(error.config?.url)) {
          toast.error("Session expired — please log in again.");
          logoutRef.current?.();
        }
        return Promise.reject(error);
      },
    );
    return () => axios.interceptors.response.eject(interceptor);
  }, []);

  const _supabaseLogout = async () => {
    const sb = await getSupabase();
    await sb.auth.signOut();
    _setAxiosToken(null);
    setUser(null);
  };

  const supabaseSubRef = useRef(null);

  useEffect(() => {
    if (!isSupabaseConfigured) {
      setLoading(false);
      toast.error("Supabase auth is not configured for this environment.");
      return;
    }

    let cancelled = false;
    getSupabase().then((sb) => {
      if (cancelled) return;

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
      supabaseSubRef.current = sub;

      sb.auth.getSession().then(({ data: { session } }) => {
        if (cancelled) return;
        if (session?.access_token) {
          _setAxiosToken(session.access_token);
          _fetchProfile().finally(() => setLoading(false));
        } else {
          setLoading(false);
        }
      });
    });

    return () => {
      cancelled = true;
      supabaseSubRef.current?.unsubscribe();
    };
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
      return await _fetchProfile();
    }
    return null;
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
          toast.error("Session expired — please log in again.");
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
    _supabaseLogout();
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
