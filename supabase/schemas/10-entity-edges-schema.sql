-- Cross-context graph view for assistant / analytics.

CREATE OR REPLACE VIEW entity_edges AS
    -- sku → vendor (via vendor_items)
    SELECT vi.sku_id       AS source_id,
           'sku'           AS source_type,
           vi.vendor_id    AS target_id,
           'vendor'        AS target_type,
           'supplied_by'   AS relation,
           vi.organization_id AS org_id
    FROM vendor_items vi
    UNION ALL
    -- vendor → sku (reverse)
    SELECT vi.vendor_id    AS source_id,
           'vendor'        AS source_type,
           vi.sku_id       AS target_id,
           'sku'           AS target_type,
           'supplies'      AS relation,
           vi.organization_id AS org_id
    FROM vendor_items vi
    UNION ALL
    -- sku → department
    SELECT s.id            AS source_id,
           'sku'           AS source_type,
           s.category_id   AS target_id,
           'department'    AS target_type,
           'in_department' AS relation,
           s.organization_id AS org_id
    FROM skus s WHERE s.category_id IS NOT NULL
    UNION ALL
    -- po → vendor
    SELECT po.id           AS source_id,
           'po'            AS source_type,
           po.vendor_id    AS target_id,
           'vendor'        AS target_type,
           'from_vendor'   AS relation,
           po.organization_id AS org_id
    FROM purchase_orders po WHERE po.vendor_id IS NOT NULL
    UNION ALL
    -- po_item → sku
    SELECT poi.po_id       AS source_id,
           'po'            AS source_type,
           poi.sku_id  AS target_id,
           'sku'           AS target_type,
           'contains_sku'  AS relation,
           poi.organization_id AS org_id
    FROM purchase_order_items poi WHERE poi.sku_id IS NOT NULL
    UNION ALL
    -- withdrawal → job
    SELECT w.id            AS source_id,
           'withdrawal'    AS source_type,
           w.job_id        AS target_id,
           'job'           AS target_type,
           'for_job'       AS relation,
           w.organization_id AS org_id
    FROM withdrawals w WHERE w.job_id IS NOT NULL
    UNION ALL
    -- job → withdrawal (reverse)
    SELECT w.job_id        AS source_id,
           'job'           AS source_type,
           w.id            AS target_id,
           'withdrawal'    AS target_type,
           'has_withdrawal' AS relation,
           w.organization_id AS org_id
    FROM withdrawals w WHERE w.job_id IS NOT NULL
    UNION ALL
    -- withdrawal → invoice (via join table)
    SELECT iw.withdrawal_id AS source_id,
           'withdrawal'     AS source_type,
           iw.invoice_id    AS target_id,
           'invoice'        AS target_type,
           'invoiced_in'    AS relation,
           i.organization_id AS org_id
    FROM invoice_withdrawals iw
    JOIN invoices i ON i.id = iw.invoice_id
    UNION ALL
    -- invoice → withdrawal (reverse)
    SELECT iw.invoice_id    AS source_id,
           'invoice'        AS source_type,
           iw.withdrawal_id AS target_id,
           'withdrawal'     AS target_type,
           'from_withdrawal' AS relation,
           i.organization_id AS org_id
    FROM invoice_withdrawals iw
    JOIN invoices i ON i.id = iw.invoice_id
    UNION ALL
    -- invoice → billing_entity
    SELECT i.id             AS source_id,
           'invoice'        AS source_type,
           i.billing_entity_id AS target_id,
           'billing_entity' AS target_type,
           'billed_to'      AS relation,
           i.organization_id AS org_id
    FROM invoices i WHERE i.billing_entity_id IS NOT NULL
    UNION ALL
    -- invoice → payment
    SELECT p.invoice_id    AS source_id,
           'invoice'       AS source_type,
           p.id            AS target_id,
           'payment'       AS target_type,
           'has_payment'   AS relation,
           p.organization_id AS org_id
    FROM payments p WHERE p.invoice_id IS NOT NULL
    UNION ALL
    -- invoice → credit_note
    SELECT cn.invoice_id   AS source_id,
           'invoice'       AS source_type,
           cn.id           AS target_id,
           'credit_note'   AS target_type,
           'has_credit_note' AS relation,
           cn.organization_id AS org_id
    FROM credit_notes cn WHERE cn.invoice_id IS NOT NULL
    UNION ALL
    -- withdrawal_item → sku
    SELECT wi.withdrawal_id AS source_id,
           'withdrawal'     AS source_type,
           wi.sku_id        AS target_id,
           'sku'            AS target_type,
           'contains_sku'   AS relation,
           w.organization_id AS org_id
    FROM withdrawal_items wi
    JOIN withdrawals w ON w.id = wi.withdrawal_id
    WHERE wi.sku_id IS NOT NULL
    UNION ALL
    -- job → billing_entity
    SELECT j.id            AS source_id,
           'job'           AS source_type,
           j.billing_entity_id AS target_id,
           'billing_entity' AS target_type,
           'billed_to'     AS relation,
           j.organization_id AS org_id
    FROM jobs j WHERE j.billing_entity_id IS NOT NULL
    UNION ALL
    -- job → invoice (via line items)
    SELECT DISTINCT ili.job_id AS source_id,
           'job'           AS source_type,
           ili.invoice_id  AS target_id,
           'invoice'       AS target_type,
           'has_invoice'   AS relation,
           i.organization_id AS org_id
    FROM invoice_line_items ili
    JOIN invoices i ON i.id = ili.invoice_id
    WHERE ili.job_id IS NOT NULL;
