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
    // Use implicit for browser email confirmation + resend. PKCE confirmation links require the
    // code verifier from the same tab that called signUp; resend() has historically emitted
    // implicit-style verify links, so PKCE mode breaks "click link" and resend for many setups.
    _supabase = createClient(supabaseUrl, supabasePublishableKey, {
      auth: {
        flowType: "implicit",
        detectSessionInUrl: true,
        persistSession: true,
        autoRefreshToken: true,
      },
    });
  }
  return _supabase;
};
