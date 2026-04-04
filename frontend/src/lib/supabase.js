const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "";
const supabasePublishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || "";

export const isSupabaseConfigured = Boolean(supabaseUrl && supabasePublishableKey);

let _supabase = null;

export const getSupabase = async () => {
  if (!isSupabaseConfigured) {
    throw new Error(
      "Supabase auth is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY.",
    );
  }
  if (!_supabase) {
    const { createClient } = await import("@supabase/supabase-js");
    _supabase = createClient(supabaseUrl, supabasePublishableKey);
  }
  return _supabase;
};
