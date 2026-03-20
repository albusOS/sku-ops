-- Align with application expectations (legacy baseline used TEXT / omitted columns).

ALTER TABLE withdrawals ADD COLUMN IF NOT EXISTS items TEXT;

ALTER TABLE invoices
    ALTER COLUMN invoice_date TYPE TIMESTAMPTZ USING (
        CASE
            WHEN invoice_date IS NULL OR btrim(invoice_date::text) = '' THEN NULL
            ELSE invoice_date::timestamptz
        END
    ),
    ALTER COLUMN due_date TYPE TIMESTAMPTZ USING (
        CASE
            WHEN due_date IS NULL OR btrim(due_date::text) = '' THEN NULL
            ELSE due_date::timestamptz
        END
    );

ALTER TABLE payments
    ALTER COLUMN payment_date TYPE TIMESTAMPTZ USING (
        CASE
            WHEN payment_date IS NULL OR btrim(payment_date::text) = '' THEN NULL
            ELSE payment_date::timestamptz
        END
    );
