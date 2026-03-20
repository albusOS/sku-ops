-- Normalized line items for material requests (was in Python schema only).

CREATE TABLE IF NOT EXISTS material_request_items (
        id TEXT PRIMARY KEY,
        material_request_id TEXT NOT NULL REFERENCES material_requests(id),
        sku_id TEXT NOT NULL,
        sku TEXT NOT NULL DEFAULT '',
        name TEXT NOT NULL DEFAULT '',
        quantity NUMERIC(18,4) NOT NULL,
        unit_price NUMERIC(18,4) NOT NULL DEFAULT 0,
        cost NUMERIC(18,4) NOT NULL DEFAULT 0,
        unit TEXT NOT NULL DEFAULT 'each'
    );

CREATE INDEX IF NOT EXISTS idx_material_request_items_mrid ON material_request_items(material_request_id);

CREATE INDEX IF NOT EXISTS idx_material_request_items_sku ON material_request_items(sku_id);
