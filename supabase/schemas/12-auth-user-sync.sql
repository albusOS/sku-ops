-- public.handle_new_user: insert / upsert app profile when Supabase Auth creates a user.
-- The AFTER INSERT trigger on auth.users is applied via migration (auth schema not in declarative diff).

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
