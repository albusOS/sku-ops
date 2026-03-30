-- Row-level security for PostgREST / Supabase client (role authenticated).
-- organization_id is read from JWT app_metadata or top-level (matches shared/api/auth_provider.py).
-- Application backend uses a DB role that bypasses RLS.

CREATE OR REPLACE FUNCTION public.jwt_organization_id()
RETURNS text
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public, auth
AS $$
  SELECT COALESCE(
    (SELECT auth.jwt()->'app_metadata'->>'organization_id'),
    (SELECT auth.jwt()->>'organization_id')
  );
$$;

GRANT EXECUTE ON FUNCTION public.jwt_organization_id() TO authenticated, anon;

-- organizations
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON organizations
  FOR ALL TO authenticated
  USING (id = public.jwt_organization_id())
  WITH CHECK (id = public.jwt_organization_id());

-- users
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON users
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

-- org_settings
ALTER TABLE org_settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON org_settings
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

-- refresh_tokens
ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON refresh_tokens
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM users u
      WHERE u.id = refresh_tokens.user_id
        AND u.organization_id = public.jwt_organization_id()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM users u
      WHERE u.id = refresh_tokens.user_id
        AND u.organization_id = public.jwt_organization_id()
    )
  );

-- oauth_states
ALTER TABLE oauth_states ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON oauth_states
  FOR ALL TO authenticated
  USING (org_id = public.jwt_organization_id())
  WITH CHECK (org_id = public.jwt_organization_id());

-- audit_log
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON audit_log
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

-- billing_entities
ALTER TABLE billing_entities ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON billing_entities
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

-- addresses
ALTER TABLE addresses ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON addresses
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

-- fiscal_periods
ALTER TABLE fiscal_periods ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON fiscal_periods
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

-- processed_events: RLS on, no policy (deny authenticated)
ALTER TABLE processed_events ENABLE ROW LEVEL SECURITY;

-- catalog
ALTER TABLE departments ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON departments
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

ALTER TABLE units_of_measure ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON units_of_measure
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

ALTER TABLE vendors ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON vendors
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

ALTER TABLE products ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON products
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

ALTER TABLE skus ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON skus
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

ALTER TABLE vendor_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON vendor_items
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

ALTER TABLE sku_counters ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON sku_counters
  FOR ALL TO authenticated
  USING (split_part(department_code, '|', 1) = public.jwt_organization_id())
  WITH CHECK (split_part(department_code, '|', 1) = public.jwt_organization_id());

-- inventory
ALTER TABLE stock_transactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON stock_transactions
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

ALTER TABLE cycle_counts ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON cycle_counts
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

ALTER TABLE cycle_count_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON cycle_count_items
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM cycle_counts cc
      WHERE cc.id = cycle_count_items.cycle_count_id
        AND cc.organization_id = public.jwt_organization_id()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM cycle_counts cc
      WHERE cc.id = cycle_count_items.cycle_count_id
        AND cc.organization_id = public.jwt_organization_id()
    )
  );

-- operations
ALTER TABLE withdrawals ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON withdrawals
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

ALTER TABLE withdrawal_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON withdrawal_items
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM withdrawals w
      WHERE w.id = withdrawal_items.withdrawal_id
        AND w.organization_id = public.jwt_organization_id()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM withdrawals w
      WHERE w.id = withdrawal_items.withdrawal_id
        AND w.organization_id = public.jwt_organization_id()
    )
  );

ALTER TABLE material_requests ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON material_requests
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

ALTER TABLE material_request_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON material_request_items
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM material_requests mr
      WHERE mr.id = material_request_items.material_request_id
        AND mr.organization_id = public.jwt_organization_id()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM material_requests mr
      WHERE mr.id = material_request_items.material_request_id
        AND mr.organization_id = public.jwt_organization_id()
    )
  );

ALTER TABLE returns ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON returns
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

ALTER TABLE return_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON return_items
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM returns r
      WHERE r.id = return_items.return_id
        AND r.organization_id = public.jwt_organization_id()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM returns r
      WHERE r.id = return_items.return_id
        AND r.organization_id = public.jwt_organization_id()
    )
  );

-- finance
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON invoices
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

ALTER TABLE invoice_withdrawals ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON invoice_withdrawals
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM invoices i
      WHERE i.id = invoice_withdrawals.invoice_id
        AND i.organization_id = public.jwt_organization_id()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM invoices i
      WHERE i.id = invoice_withdrawals.invoice_id
        AND i.organization_id = public.jwt_organization_id()
    )
  );

ALTER TABLE invoice_line_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON invoice_line_items
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM invoices i
      WHERE i.id = invoice_line_items.invoice_id
        AND i.organization_id = public.jwt_organization_id()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM invoices i
      WHERE i.id = invoice_line_items.invoice_id
        AND i.organization_id = public.jwt_organization_id()
    )
  );

ALTER TABLE invoice_counters ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON invoice_counters
  FOR ALL TO authenticated
  USING (split_part(key, '|', 1) = public.jwt_organization_id())
  WITH CHECK (split_part(key, '|', 1) = public.jwt_organization_id());

ALTER TABLE credit_notes ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON credit_notes
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

ALTER TABLE credit_note_line_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON credit_note_line_items
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM credit_notes cn
      WHERE cn.id = credit_note_line_items.credit_note_id
        AND cn.organization_id = public.jwt_organization_id()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM credit_notes cn
      WHERE cn.id = credit_note_line_items.credit_note_id
        AND cn.organization_id = public.jwt_organization_id()
    )
  );

ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON payments
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

ALTER TABLE payment_withdrawals ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON payment_withdrawals
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM payments p
      WHERE p.id = payment_withdrawals.payment_id
        AND p.organization_id = public.jwt_organization_id()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM payments p
      WHERE p.id = payment_withdrawals.payment_id
        AND p.organization_id = public.jwt_organization_id()
    )
  );

ALTER TABLE financial_ledger ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON financial_ledger
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

-- purchasing
ALTER TABLE purchase_orders ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON purchase_orders
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

ALTER TABLE purchase_order_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON purchase_order_items
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

-- documents
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON documents
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

-- jobs
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON jobs
  FOR ALL TO authenticated
  USING (organization_id = public.jwt_organization_id())
  WITH CHECK (organization_id = public.jwt_organization_id());

-- assistant
ALTER TABLE memory_artifacts ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON memory_artifacts
  FOR ALL TO authenticated
  USING (org_id = public.jwt_organization_id())
  WITH CHECK (org_id = public.jwt_organization_id());

ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON agent_runs
  FOR ALL TO authenticated
  USING (org_id = public.jwt_organization_id())
  WITH CHECK (org_id = public.jwt_organization_id());

ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON embeddings
  FOR ALL TO authenticated
  USING (org_id = public.jwt_organization_id())
  WITH CHECK (org_id = public.jwt_organization_id());
