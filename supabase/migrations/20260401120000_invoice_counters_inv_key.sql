-- Demo seed used key 'invoice_number'; application uses 'inv' (invoice_next_number).
-- Without this merge, the app allocates INV-00001 again and collides with seeded invoices.
INSERT INTO invoice_counters (organization_id, key, counter)
SELECT organization_id, 'inv', counter
FROM invoice_counters
WHERE key = 'invoice_number'
ON CONFLICT (organization_id, key) DO UPDATE SET
    counter = GREATEST(invoice_counters.counter, EXCLUDED.counter);

DELETE FROM invoice_counters WHERE key = 'invoice_number';
