const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "";
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || "";

/**
 * True when Supabase credentials are present in the environment.
 * When false, AuthContext falls back to /api/auth/login bridge mode.
 */
export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);

// Lazy-load Supabase SDK only when configured. The module name is constructed
// dynamically so Rollup/Vite won't try to resolve it at build time.
let _supabase = null;
const _pkg = ["@supabase", "supabase-js"].join("/");

export const getSupabase = async () => {
  if (!_supabase && isSupabaseConfigured) {
    const mod = await import(/* @vite-ignore */ _pkg);
    _supabase = mod.createClient(supabaseUrl, supabaseAnonKey);
  }
  return _supabase;
};
