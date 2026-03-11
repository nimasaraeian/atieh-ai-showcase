-- Service dimension for clean analytics
-- Maps raw free-text service values to standardized categories

CREATE TABLE IF NOT EXISTS service_dim (
  raw_service_text TEXT PRIMARY KEY,
  clean_service_category TEXT NOT NULL DEFAULT 'سایر',
  clean_service_subtype TEXT,
  duration_hint_minutes INTEGER,
  is_noise INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_service_dim_category ON service_dim(clean_service_category);
CREATE INDEX IF NOT EXISTS idx_service_dim_is_noise ON service_dim(is_noise);

-- View for analytics: raw -> clean mapping, excluding noise
DROP VIEW IF EXISTS v_clean_services;
CREATE VIEW v_clean_services AS
SELECT
  raw_service_text,
  clean_service_category,
  clean_service_subtype,
  duration_hint_minutes,
  is_noise
FROM service_dim
WHERE is_noise = 0;
