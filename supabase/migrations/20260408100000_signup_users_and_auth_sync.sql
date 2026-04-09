-- Sign-up schema: drop unused refresh_tokens (Supabase owns sessions); user profile columns;
-- sync auth.users -> public.users. oauth_states kept for Xero OAuth.

DROP POLICY IF EXISTS tenant_isolation ON refresh_tokens;
ALTER TABLE IF EXISTS refresh_tokens DISABLE ROW LEVEL SECURITY;
DROP TABLE IF EXISTS refresh_tokens;

ALTER TABLE public.users DROP COLUMN IF EXISTS password;
ALTER TABLE public.users DROP COLUMN IF EXISTS billing_entity;

-- Contractor org picker for users without organization_id in JWT yet (PostgREST / RLS).
DROP POLICY IF EXISTS organizations_select_for_authenticated ON organizations;
CREATE POLICY organizations_select_for_authenticated ON organizations
  FOR SELECT TO authenticated
  USING (true);

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.users (id, email, name, role, is_active, created_at)
  VALUES (
    NEW.id,
    COALESCE(NEW.email, ''),
    COALESCE(NEW.raw_user_meta_data->>'name', ''),
    COALESCE(
      NULLIF(TRIM(NEW.raw_app_meta_data->>'role'), ''),
      NULLIF(TRIM(NEW.raw_user_meta_data->>'role'), ''),
      'admin'
    ),
    TRUE,
    COALESCE(NEW.created_at, NOW())
  )
  ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    name = COALESCE(NULLIF(EXCLUDED.name, ''), public.users.name),
    role = COALESCE(NULLIF(EXCLUDED.role, ''), public.users.role);
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();
