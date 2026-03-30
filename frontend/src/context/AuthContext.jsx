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

  const _supabaseLogout = async () => {
    if (!isSupabaseConfigured) {
      _setAxiosToken(null);
      setUser(null);
      return;
    }
    const sb = await getSupabase();
    await sb.auth.signOut();
    _setAxiosToken(null);
    setUser(null);
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

  const supabaseSubRef = useRef(null);

  useEffect(() => {
    if (!isSupabaseConfigured) {
      setLoading(false);
      toast.error(
        "Supabase auth is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY (see frontend/.env.example).",
      );
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

  const login = async (email, password) => {
    if (!isSupabaseConfigured) {
      throw new Error("Supabase auth is not configured.");
    }
    const sb = await getSupabase();
    const { data, error } = await sb.auth.signInWithPassword({ email, password });
    if (error) throw error;
    _setAxiosToken(data.session.access_token);
    const profile = await _fetchProfile();
    return profile;
  };

  const register = async (email, password, name) => {
    if (!isSupabaseConfigured) {
      throw new Error("Supabase auth is not configured.");
    }
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

  const logout = () => {
    void _supabaseLogout();
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
