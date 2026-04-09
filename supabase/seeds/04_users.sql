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
    '0195f2c0-89ab-7a10-8a01-000000000001'::uuid,
    v_instance,
    'authenticated',
    'authenticated',
    'admin@supplyyard.com',
    crypt('dev123', gen_salt('bf')),
    NOW(),
    '{"provider":"email","providers":["email"],"role":"admin","organization_id":"0195f2c0-89aa-7d6d-bb34-7f3b3f69c001"}'::jsonb,
    '{"name":"Marcus Chen"}'::jsonb,
    NOW(),
    NOW(),
    '', '', '', '', '', '', '', ''
  ) ON CONFLICT (id) DO NOTHING;

  INSERT INTO auth.identities (
    id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
  ) VALUES (
    '0195f2c0-89ab-7a10-8a01-000000000001'::uuid,
    '0195f2c0-89ab-7a10-8a01-000000000001'::uuid,
    jsonb_build_object(
      'sub', '0195f2c0-89ab-7a10-8a01-000000000001',
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
    '0195f2c0-89ab-7a10-8a01-000000000002'::uuid,
    v_instance,
    'authenticated',
    'authenticated',
    'mike@rivridge.com',
    crypt('dev123', gen_salt('bf')),
    NOW(),
    '{"provider":"email","providers":["email"],"role":"contractor","organization_id":"0195f2c0-89aa-7d6d-bb34-7f3b3f69c001"}'::jsonb,
    '{"name":"Mike Torres"}'::jsonb,
    NOW(),
    NOW(),
    '', '', '', '', '', '', '', ''
  ) ON CONFLICT (id) DO NOTHING;

  INSERT INTO auth.identities (
    id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
  ) VALUES (
    '0195f2c0-89ab-7a10-8a01-000000000002'::uuid,
    '0195f2c0-89ab-7a10-8a01-000000000002'::uuid,
    jsonb_build_object(
      'sub', '0195f2c0-89ab-7a10-8a01-000000000002',
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
    '0195f2c0-89ab-7a10-8a01-000000000003'::uuid,
    v_instance,
    'authenticated',
    'authenticated',
    'sarah@summitpm.com',
    crypt('dev123', gen_salt('bf')),
    NOW(),
    '{"provider":"email","providers":["email"],"role":"contractor","organization_id":"0195f2c0-89aa-7d6d-bb34-7f3b3f69c001"}'::jsonb,
    '{"name":"Sarah Okafor"}'::jsonb,
    NOW(),
    NOW(),
    '', '', '', '', '', '', '', ''
  ) ON CONFLICT (id) DO NOTHING;

  INSERT INTO auth.identities (
    id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
  ) VALUES (
    '0195f2c0-89ab-7a10-8a01-000000000003'::uuid,
    '0195f2c0-89ab-7a10-8a01-000000000003'::uuid,
    jsonb_build_object(
      'sub', '0195f2c0-89ab-7a10-8a01-000000000003',
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
    '0195f2c0-89ab-7a10-8a01-000000000004'::uuid,
    v_instance,
    'authenticated',
    'authenticated',
    'dev@supply-yard.local',
    crypt('dev123', gen_salt('bf')),
    NOW(),
    '{"provider":"email","providers":["email"],"role":"admin","organization_id":"0195f2c0-89aa-7d6d-bb34-7f3b3f69c001"}'::jsonb,
    '{"name":"Dev Admin"}'::jsonb,
    NOW(),
    NOW(),
    '', '', '', '', '', '', '', ''
  ) ON CONFLICT (id) DO NOTHING;

  INSERT INTO auth.identities (
    id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
  ) VALUES (
    '0195f2c0-89ab-7a10-8a01-000000000004'::uuid,
    '0195f2c0-89ab-7a10-8a01-000000000004'::uuid,
    jsonb_build_object(
      'sub', '0195f2c0-89ab-7a10-8a01-000000000004',
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
    '0195f2c0-89ab-7a10-8a01-000000000005'::uuid,
    v_instance,
    'authenticated',
    'authenticated',
    'contractor@supply-yard.local',
    crypt('dev123', gen_salt('bf')),
    NOW(),
    '{"provider":"email","providers":["email"],"role":"contractor","organization_id":"0195f2c0-89aa-7d6d-bb34-7f3b3f69c001"}'::jsonb,
    '{"name":"Dev Contractor"}'::jsonb,
    NOW(),
    NOW(),
    '', '', '', '', '', '', '', ''
  ) ON CONFLICT (id) DO NOTHING;

  INSERT INTO auth.identities (
    id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
  ) VALUES (
    '0195f2c0-89ab-7a10-8a01-000000000005'::uuid,
    '0195f2c0-89ab-7a10-8a01-000000000005'::uuid,
    jsonb_build_object(
      'sub', '0195f2c0-89ab-7a10-8a01-000000000005',
      'email', 'contractor@supply-yard.local'
    ),
    'email',
    'contractor@supply-yard.local',
    NOW(),
    NOW(),
    NOW()
  ) ON CONFLICT (provider_id, provider) DO NOTHING;

  -- E2E onboarding admin (no organization_id in app_metadata)
  INSERT INTO auth.users (
    id, instance_id, aud, role, email, encrypted_password,
    email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
    created_at, updated_at,
    confirmation_token, recovery_token, email_change_token_new,
    email_change_token_current, phone_change_token, reauthentication_token,
    email_change, phone_change
  ) VALUES (
    '0195f2c0-89ab-7a10-8a01-0e2e00000001'::uuid,
    v_instance,
    'authenticated',
    'authenticated',
    'e2e-onboard-admin@test.local',
    crypt('dev123', gen_salt('bf')),
    NOW(),
    '{"provider":"email","providers":["email"],"role":"admin"}'::jsonb,
    '{"name":"E2E Onboard Admin"}'::jsonb,
    NOW(),
    NOW(),
    '', '', '', '', '', '', '', ''
  ) ON CONFLICT (id) DO NOTHING;

  INSERT INTO auth.identities (
    id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
  ) VALUES (
    '0195f2c0-89ab-7a10-8a01-0e2e00000001'::uuid,
    '0195f2c0-89ab-7a10-8a01-0e2e00000001'::uuid,
    jsonb_build_object(
      'sub', '0195f2c0-89ab-7a10-8a01-0e2e00000001',
      'email', 'e2e-onboard-admin@test.local'
    ),
    'email',
    'e2e-onboard-admin@test.local',
    NOW(),
    NOW(),
    NOW()
  ) ON CONFLICT (provider_id, provider) DO NOTHING;

  -- E2E onboarding contractor (no organization_id in app_metadata)
  INSERT INTO auth.users (
    id, instance_id, aud, role, email, encrypted_password,
    email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
    created_at, updated_at,
    confirmation_token, recovery_token, email_change_token_new,
    email_change_token_current, phone_change_token, reauthentication_token,
    email_change, phone_change
  ) VALUES (
    '0195f2c0-89ab-7a10-8a01-0e2e00000002'::uuid,
    v_instance,
    'authenticated',
    'authenticated',
    'e2e-onboard-ctr@test.local',
    crypt('dev123', gen_salt('bf')),
    NOW(),
    '{"provider":"email","providers":["email"],"role":"contractor"}'::jsonb,
    '{"name":"E2E Onboard Contractor"}'::jsonb,
    NOW(),
    NOW(),
    '', '', '', '', '', '', '', ''
  ) ON CONFLICT (id) DO NOTHING;

  INSERT INTO auth.identities (
    id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at
  ) VALUES (
    '0195f2c0-89ab-7a10-8a01-0e2e00000002'::uuid,
    '0195f2c0-89ab-7a10-8a01-0e2e00000002'::uuid,
    jsonb_build_object(
      'sub', '0195f2c0-89ab-7a10-8a01-0e2e00000002',
      'email', 'e2e-onboard-ctr@test.local'
    ),
    'email',
    'e2e-onboard-ctr@test.local',
    NOW(),
    NOW(),
    NOW()
  ) ON CONFLICT (provider_id, provider) DO NOTHING;
END $$;

-- Upsert app profile (auth.users inserted above; trigger may have created the row).
INSERT INTO users (id, email, name, role, company, phone, is_active, organization_id, created_at) VALUES ('0195f2c0-89ab-7a10-8a01-000000000001', 'admin@supplyyard.com', 'Marcus Chen', 'admin', '', '', TRUE, '0195f2c0-89aa-7d6d-bb34-7f3b3f69c001', '2025-12-17T12:00:00+00:00') ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, name = EXCLUDED.name, role = EXCLUDED.role, company = EXCLUDED.company, phone = EXCLUDED.phone, is_active = EXCLUDED.is_active, organization_id = EXCLUDED.organization_id;
INSERT INTO users (id, email, name, role, company, phone, is_active, organization_id, created_at) VALUES ('0195f2c0-89ab-7a10-8a01-000000000002', 'mike@rivridge.com', 'Mike Torres', 'contractor', 'Riva Ridge Property Mgmt', '', TRUE, '0195f2c0-89aa-7d6d-bb34-7f3b3f69c001', '2025-12-17T12:00:00+00:00') ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, name = EXCLUDED.name, role = EXCLUDED.role, company = EXCLUDED.company, phone = EXCLUDED.phone, is_active = EXCLUDED.is_active, organization_id = EXCLUDED.organization_id;
INSERT INTO users (id, email, name, role, company, phone, is_active, organization_id, created_at) VALUES ('0195f2c0-89ab-7a10-8a01-000000000003', 'sarah@summitpm.com', 'Sarah Okafor', 'contractor', 'Summit Property Group', '', TRUE, '0195f2c0-89aa-7d6d-bb34-7f3b3f69c001', '2025-12-17T12:00:00+00:00') ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, name = EXCLUDED.name, role = EXCLUDED.role, company = EXCLUDED.company, phone = EXCLUDED.phone, is_active = EXCLUDED.is_active, organization_id = EXCLUDED.organization_id;

INSERT INTO users (id, email, name, role, company, phone, is_active, organization_id, created_at) VALUES ('0195f2c0-89ab-7a10-8a01-000000000004', 'dev@supply-yard.local', 'Dev Admin', 'admin', '', '', TRUE, '0195f2c0-89aa-7d6d-bb34-7f3b3f69c001', '2025-12-17T12:00:00+00:00') ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, name = EXCLUDED.name, role = EXCLUDED.role, company = EXCLUDED.company, phone = EXCLUDED.phone, is_active = EXCLUDED.is_active, organization_id = EXCLUDED.organization_id;
INSERT INTO users (id, email, name, role, company, phone, is_active, organization_id, created_at) VALUES ('0195f2c0-89ab-7a10-8a01-000000000005', 'contractor@supply-yard.local', 'Dev Contractor', 'contractor', 'Dev Contractor Co', '', TRUE, '0195f2c0-89aa-7d6d-bb34-7f3b3f69c001', '2025-12-17T12:00:00+00:00') ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, name = EXCLUDED.name, role = EXCLUDED.role, company = EXCLUDED.company, phone = EXCLUDED.phone, is_active = EXCLUDED.is_active, organization_id = EXCLUDED.organization_id;

-- E2E onboarding test users (no organization_id - triggers onboarding dialog)
INSERT INTO users (id, email, name, role, company, phone, is_active, organization_id, created_at) VALUES ('0195f2c0-89ab-7a10-8a01-0e2e00000001', 'e2e-onboard-admin@test.local', 'E2E Onboard Admin', 'admin', '', '', TRUE, NULL, NOW()) ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, name = EXCLUDED.name, role = EXCLUDED.role, company = EXCLUDED.company, phone = EXCLUDED.phone, is_active = EXCLUDED.is_active, organization_id = EXCLUDED.organization_id;
INSERT INTO users (id, email, name, role, company, phone, is_active, organization_id, created_at) VALUES ('0195f2c0-89ab-7a10-8a01-0e2e00000002', 'e2e-onboard-ctr@test.local', 'E2E Onboard Contractor', 'contractor', '', '', TRUE, NULL, NOW()) ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, name = EXCLUDED.name, role = EXCLUDED.role, company = EXCLUDED.company, phone = EXCLUDED.phone, is_active = EXCLUDED.is_active, organization_id = EXCLUDED.organization_id;
