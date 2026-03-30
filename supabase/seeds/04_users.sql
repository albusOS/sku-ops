-- Seed: Supabase Auth (auth.users + identities) then public.users (app profiles)
-- Every public.users row has a matching auth user id so signInWithPassword works after db reset.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
DECLARE
  v_instance UUID := '00000000-0000-0000-0000-000000000000'::uuid;
BEGIN
  -- Demo admin
  INSERT INTO auth.users (
    id, instance_id, aud, role, email, encrypted_password,
    email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
    created_at, updated_at,
    confirmation_token, recovery_token, email_change_token_new,
    email_change_token_current, phone_change_token, reauthentication_token,
    email_change, phone_change
  ) VALUES (
    'db3a2209-7b14-42e3-9c7b-8ab0b774f22b'::uuid,
    v_instance,
    'authenticated',
    'authenticated',
    'admin@supplyyard.com',
    crypt('dev123', gen_salt('bf')),
    NOW(),
    '{"provider":"email","providers":["email"],"role":"admin","organization_id":"supply-yard"}'::jsonb,
    '{"name":"Marcus Chen"}'::jsonb,
    NOW(),
    NOW(),
    '', '', '', '', '', '', '', ''
  ) ON CONFLICT (id) DO NOTHING;

  INSERT INTO auth.identities (
    id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
  ) VALUES (
    'db3a2209-7b14-42e3-9c7b-8ab0b774f22b'::uuid,
    'db3a2209-7b14-42e3-9c7b-8ab0b774f22b'::uuid,
    jsonb_build_object(
      'sub', 'db3a2209-7b14-42e3-9c7b-8ab0b774f22b',
      'email', 'admin@supplyyard.com'
    ),
    'email',
    'admin@supplyyard.com',
    NOW(),
    NOW(),
    NOW()
  ) ON CONFLICT (provider_id, provider) DO NOTHING;

  -- Demo contractors
  INSERT INTO auth.users (
    id, instance_id, aud, role, email, encrypted_password,
    email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
    created_at, updated_at,
    confirmation_token, recovery_token, email_change_token_new,
    email_change_token_current, phone_change_token, reauthentication_token,
    email_change, phone_change
  ) VALUES (
    '4d5ff6c9-6ac2-4929-bd5f-e4197c10d009'::uuid,
    v_instance,
    'authenticated',
    'authenticated',
    'mike@rivridge.com',
    crypt('dev123', gen_salt('bf')),
    NOW(),
    '{"provider":"email","providers":["email"],"role":"contractor","organization_id":"supply-yard"}'::jsonb,
    '{"name":"Mike Torres"}'::jsonb,
    NOW(),
    NOW(),
    '', '', '', '', '', '', '', ''
  ) ON CONFLICT (id) DO NOTHING;

  INSERT INTO auth.identities (
    id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
  ) VALUES (
    '4d5ff6c9-6ac2-4929-bd5f-e4197c10d009'::uuid,
    '4d5ff6c9-6ac2-4929-bd5f-e4197c10d009'::uuid,
    jsonb_build_object(
      'sub', '4d5ff6c9-6ac2-4929-bd5f-e4197c10d009',
      'email', 'mike@rivridge.com'
    ),
    'email',
    'mike@rivridge.com',
    NOW(),
    NOW(),
    NOW()
  ) ON CONFLICT (provider_id, provider) DO NOTHING;

  INSERT INTO auth.users (
    id, instance_id, aud, role, email, encrypted_password,
    email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
    created_at, updated_at,
    confirmation_token, recovery_token, email_change_token_new,
    email_change_token_current, phone_change_token, reauthentication_token,
    email_change, phone_change
  ) VALUES (
    '0565b2d4-2c7d-4b5e-9aa7-a2a05d387224'::uuid,
    v_instance,
    'authenticated',
    'authenticated',
    'sarah@summitpm.com',
    crypt('dev123', gen_salt('bf')),
    NOW(),
    '{"provider":"email","providers":["email"],"role":"contractor","organization_id":"supply-yard"}'::jsonb,
    '{"name":"Sarah Okafor"}'::jsonb,
    NOW(),
    NOW(),
    '', '', '', '', '', '', '', ''
  ) ON CONFLICT (id) DO NOTHING;

  INSERT INTO auth.identities (
    id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
  ) VALUES (
    '0565b2d4-2c7d-4b5e-9aa7-a2a05d387224'::uuid,
    '0565b2d4-2c7d-4b5e-9aa7-a2a05d387224'::uuid,
    jsonb_build_object(
      'sub', '0565b2d4-2c7d-4b5e-9aa7-a2a05d387224',
      'email', 'sarah@summitpm.com'
    ),
    'email',
    'sarah@summitpm.com',
    NOW(),
    NOW(),
    NOW()
  ) ON CONFLICT (provider_id, provider) DO NOTHING;

  -- Dev admin
  INSERT INTO auth.users (
    id, instance_id, aud, role, email, encrypted_password,
    email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
    created_at, updated_at,
    confirmation_token, recovery_token, email_change_token_new,
    email_change_token_current, phone_change_token, reauthentication_token,
    email_change, phone_change
  ) VALUES (
    'c0ffeed0-0000-4000-8000-000000000001'::uuid,
    v_instance,
    'authenticated',
    'authenticated',
    'dev@supply-yard.local',
    crypt('dev123', gen_salt('bf')),
    NOW(),
    '{"provider":"email","providers":["email"],"role":"admin","organization_id":"supply-yard"}'::jsonb,
    '{"name":"Dev Admin"}'::jsonb,
    NOW(),
    NOW(),
    '', '', '', '', '', '', '', ''
  ) ON CONFLICT (id) DO NOTHING;

  INSERT INTO auth.identities (
    id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
  ) VALUES (
    'c0ffeed0-0000-4000-8000-000000000001'::uuid,
    'c0ffeed0-0000-4000-8000-000000000001'::uuid,
    jsonb_build_object(
      'sub', 'c0ffeed0-0000-4000-8000-000000000001',
      'email', 'dev@supply-yard.local'
    ),
    'email',
    'dev@supply-yard.local',
    NOW(),
    NOW(),
    NOW()
  ) ON CONFLICT (provider_id, provider) DO NOTHING;

  -- Dev contractor
  INSERT INTO auth.users (
    id, instance_id, aud, role, email, encrypted_password,
    email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
    created_at, updated_at,
    confirmation_token, recovery_token, email_change_token_new,
    email_change_token_current, phone_change_token, reauthentication_token,
    email_change, phone_change
  ) VALUES (
    'c0ffeed0-0000-4000-8000-000000000002'::uuid,
    v_instance,
    'authenticated',
    'authenticated',
    'contractor@supply-yard.local',
    crypt('dev123', gen_salt('bf')),
    NOW(),
    '{"provider":"email","providers":["email"],"role":"contractor","organization_id":"supply-yard"}'::jsonb,
    '{"name":"Dev Contractor"}'::jsonb,
    NOW(),
    NOW(),
    '', '', '', '', '', '', '', ''
  ) ON CONFLICT (id) DO NOTHING;

  INSERT INTO auth.identities (
    id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
  ) VALUES (
    'c0ffeed0-0000-4000-8000-000000000002'::uuid,
    'c0ffeed0-0000-4000-8000-000000000002'::uuid,
    jsonb_build_object(
      'sub', 'c0ffeed0-0000-4000-8000-000000000002',
      'email', 'contractor@supply-yard.local'
    ),
    'email',
    'contractor@supply-yard.local',
    NOW(),
    NOW(),
    NOW()
  ) ON CONFLICT (provider_id, provider) DO NOTHING;
END $$;

-- bcrypt for dev123 (matches Supabase seed password)
INSERT INTO users (id, email, password, name, role, company, billing_entity, phone, is_active, organization_id, created_at) VALUES ('db3a2209-7b14-42e3-9c7b-8ab0b774f22b', 'admin@supplyyard.com', '$2b$12$Q77dY9Q3LOTHynFtYgweNeUc02f/KZ25pu.3a4HHRh1S80r1nLWoW', 'Marcus Chen', 'admin', '', '', '', TRUE, 'supply-yard', '2025-12-17T12:00:00+00:00') ON CONFLICT (email) DO UPDATE SET password = EXCLUDED.password, name = EXCLUDED.name, role = EXCLUDED.role;
INSERT INTO users (id, email, password, name, role, company, billing_entity, phone, is_active, organization_id, created_at) VALUES ('4d5ff6c9-6ac2-4929-bd5f-e4197c10d009', 'mike@rivridge.com', '$2b$12$Q77dY9Q3LOTHynFtYgweNeUc02f/KZ25pu.3a4HHRh1S80r1nLWoW', 'Mike Torres', 'contractor', 'Riva Ridge Property Mgmt', 'Riva Ridge Property Mgmt', '', TRUE, 'supply-yard', '2025-12-17T12:00:00+00:00') ON CONFLICT (email) DO UPDATE SET password = EXCLUDED.password, name = EXCLUDED.name, role = EXCLUDED.role;
INSERT INTO users (id, email, password, name, role, company, billing_entity, phone, is_active, organization_id, created_at) VALUES ('0565b2d4-2c7d-4b5e-9aa7-a2a05d387224', 'sarah@summitpm.com', '$2b$12$Q77dY9Q3LOTHynFtYgweNeUc02f/KZ25pu.3a4HHRh1S80r1nLWoW', 'Sarah Okafor', 'contractor', 'Summit Property Group', 'Summit Property Group', '', TRUE, 'supply-yard', '2025-12-17T12:00:00+00:00') ON CONFLICT (email) DO UPDATE SET password = EXCLUDED.password, name = EXCLUDED.name, role = EXCLUDED.role;

INSERT INTO users (id, email, password, name, role, company, billing_entity, phone, is_active, organization_id, created_at) VALUES ('c0ffeed0-0000-4000-8000-000000000001', 'dev@supply-yard.local', '$2b$12$Q77dY9Q3LOTHynFtYgweNeUc02f/KZ25pu.3a4HHRh1S80r1nLWoW', 'Dev Admin', 'admin', '', '', '', TRUE, 'supply-yard', '2025-12-17T12:00:00+00:00') ON CONFLICT (email) DO UPDATE SET password = EXCLUDED.password, name = EXCLUDED.name, role = EXCLUDED.role;
INSERT INTO users (id, email, password, name, role, company, billing_entity, phone, is_active, organization_id, created_at) VALUES ('c0ffeed0-0000-4000-8000-000000000002', 'contractor@supply-yard.local', '$2b$12$Q77dY9Q3LOTHynFtYgweNeUc02f/KZ25pu.3a4HHRh1S80r1nLWoW', 'Dev Contractor', 'contractor', 'Dev Contractor Co', 'Dev Contractor Co', '', TRUE, 'supply-yard', '2025-12-17T12:00:00+00:00') ON CONFLICT (email) DO UPDATE SET password = EXCLUDED.password, name = EXCLUDED.name, role = EXCLUDED.role;
