BEGIN;

-- Finance: invoices, credit notes, payments, and ledger are accounting source-of-truth data.
ALTER TABLE invoices
    ALTER COLUMN subtotal TYPE NUMERIC(18,2) USING ROUND(subtotal::numeric, 2),
    ALTER COLUMN tax TYPE NUMERIC(18,2) USING ROUND(tax::numeric, 2),
    ALTER COLUMN tax_rate TYPE NUMERIC(9,4) USING ROUND(tax_rate::numeric, 4),
    ALTER COLUMN total TYPE NUMERIC(18,2) USING ROUND(total::numeric, 2),
    ALTER COLUMN amount_credited TYPE NUMERIC(18,2) USING ROUND(amount_credited::numeric, 2);

ALTER TABLE invoice_line_items
    ALTER COLUMN quantity TYPE NUMERIC(18,4) USING ROUND(quantity::numeric, 4),
    ALTER COLUMN unit_price TYPE NUMERIC(18,4) USING ROUND(unit_price::numeric, 4),
    ALTER COLUMN amount TYPE NUMERIC(18,2) USING ROUND(amount::numeric, 2),
    ALTER COLUMN cost TYPE NUMERIC(18,4) USING ROUND(cost::numeric, 4),
    ALTER COLUMN sell_cost TYPE NUMERIC(18,4) USING ROUND(sell_cost::numeric, 4);

ALTER TABLE credit_notes
    ALTER COLUMN subtotal TYPE NUMERIC(18,2) USING ROUND(subtotal::numeric, 2),
    ALTER COLUMN tax TYPE NUMERIC(18,2) USING ROUND(tax::numeric, 2),
    ALTER COLUMN total TYPE NUMERIC(18,2) USING ROUND(total::numeric, 2);

ALTER TABLE credit_note_line_items
    ALTER COLUMN quantity TYPE NUMERIC(18,4) USING ROUND(quantity::numeric, 4),
    ALTER COLUMN unit_price TYPE NUMERIC(18,4) USING ROUND(unit_price::numeric, 4),
    ALTER COLUMN amount TYPE NUMERIC(18,2) USING ROUND(amount::numeric, 2),
    ALTER COLUMN cost TYPE NUMERIC(18,4) USING ROUND(cost::numeric, 4),
    ALTER COLUMN sell_cost TYPE NUMERIC(18,4) USING ROUND(sell_cost::numeric, 4);

ALTER TABLE payments
    ALTER COLUMN amount TYPE NUMERIC(18,2) USING ROUND(amount::numeric, 2);

ALTER TABLE financial_ledger
    ALTER COLUMN amount TYPE NUMERIC(18,2) USING ROUND(amount::numeric, 2),
    ALTER COLUMN quantity TYPE NUMERIC(18,4) USING ROUND(quantity::numeric, 4),
    ALTER COLUMN unit_cost TYPE NUMERIC(18,4) USING ROUND(unit_cost::numeric, 4);

-- Operations: keep line-item and aggregate financial values aligned with finance precision.
ALTER TABLE withdrawals
    ALTER COLUMN subtotal TYPE NUMERIC(18,2) USING ROUND(subtotal::numeric, 2),
    ALTER COLUMN tax TYPE NUMERIC(18,2) USING ROUND(tax::numeric, 2),
    ALTER COLUMN tax_rate TYPE NUMERIC(9,4) USING ROUND(tax_rate::numeric, 4),
    ALTER COLUMN total TYPE NUMERIC(18,2) USING ROUND(total::numeric, 2),
    ALTER COLUMN cost_total TYPE NUMERIC(18,2) USING ROUND(cost_total::numeric, 2);

ALTER TABLE returns
    ALTER COLUMN subtotal TYPE NUMERIC(18,2) USING ROUND(subtotal::numeric, 2),
    ALTER COLUMN tax TYPE NUMERIC(18,2) USING ROUND(tax::numeric, 2),
    ALTER COLUMN total TYPE NUMERIC(18,2) USING ROUND(total::numeric, 2),
    ALTER COLUMN cost_total TYPE NUMERIC(18,2) USING ROUND(cost_total::numeric, 2);

ALTER TABLE withdrawal_items
    ALTER COLUMN quantity TYPE NUMERIC(18,4) USING ROUND(quantity::numeric, 4),
    ALTER COLUMN unit_price TYPE NUMERIC(18,4) USING ROUND(unit_price::numeric, 4),
    ALTER COLUMN cost TYPE NUMERIC(18,4) USING ROUND(cost::numeric, 4),
    ALTER COLUMN amount TYPE NUMERIC(18,2) USING ROUND(amount::numeric, 2),
    ALTER COLUMN cost_total TYPE NUMERIC(18,2) USING ROUND(cost_total::numeric, 2),
    ALTER COLUMN sell_cost TYPE NUMERIC(18,4) USING ROUND(sell_cost::numeric, 4);

ALTER TABLE return_items
    ALTER COLUMN quantity TYPE NUMERIC(18,4) USING ROUND(quantity::numeric, 4),
    ALTER COLUMN unit_price TYPE NUMERIC(18,4) USING ROUND(unit_price::numeric, 4),
    ALTER COLUMN cost TYPE NUMERIC(18,4) USING ROUND(cost::numeric, 4),
    ALTER COLUMN amount TYPE NUMERIC(18,2) USING ROUND(amount::numeric, 2),
    ALTER COLUMN cost_total TYPE NUMERIC(18,2) USING ROUND(cost_total::numeric, 2),
    ALTER COLUMN sell_cost TYPE NUMERIC(18,4) USING ROUND(sell_cost::numeric, 4);

COMMIT;
