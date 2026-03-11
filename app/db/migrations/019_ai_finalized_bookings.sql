-- Migration 019: AI Finalized Bookings table
-- Stores bookings created via "ثبت نهایی نوبت" from receptionist UI.
-- Columns: record_no, patient_name, doctor_name, service, date, time, created_at, source, status

CREATE TABLE IF NOT EXISTS ai_finalized_bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_no TEXT NOT NULL,
    patient_name TEXT NOT NULL,
    doctor_name TEXT NOT NULL,
    service TEXT NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    source TEXT NOT NULL DEFAULT 'AI',
    status TEXT NOT NULL DEFAULT 'confirmed'
);

CREATE INDEX IF NOT EXISTS idx_ai_finalized_bookings_created ON ai_finalized_bookings(created_at DESC);
