-- Migration 005: Performance indexes for appointment_date and status columns.
--
-- These indexes eliminate full-table scans on the two most-queried filter/sort
-- columns in the appointments table (71k+ rows):
--
--   idx_appointments_date   -> /ai/top-patients  date-range WHERE clause
--                           -> GET /appointments  future_only  filter
--   idx_appointments_status -> extract_features() status IN (completed,cancelled)
--                           -> GET /appointments  status filter
--
-- Both statements use IF NOT EXISTS, so re-running is fully safe.

CREATE INDEX IF NOT EXISTS idx_appointments_date
    ON appointments(appointment_date);

CREATE INDEX IF NOT EXISTS idx_appointments_status
    ON appointments(status);
