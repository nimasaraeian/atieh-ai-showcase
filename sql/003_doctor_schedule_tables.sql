PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS doctor_master (
    doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_name TEXT NOT NULL UNIQUE,
    floor_label TEXT,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS doctor_shift_schedule (
    shift_id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id INTEGER NOT NULL,
    source_sheet TEXT,
    weekday_name TEXT,
    shift_label TEXT,
    shift_start TEXT,
    shift_end TEXT,
    floor_label TEXT,
    raw_text TEXT,
    source_file TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doctor_id) REFERENCES doctor_master(doctor_id)
);

CREATE TABLE IF NOT EXISTS doctor_time_slots (
    slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id INTEGER NOT NULL,
    source_sheet TEXT,
    weekday_name TEXT,
    shift_label TEXT,
    slot_start TEXT NOT NULL,
    floor_label TEXT,
    unit_label TEXT,
    availability_status TEXT NOT NULL DEFAULT 'available',
    raw_text TEXT,
    source_file TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doctor_id) REFERENCES doctor_master(doctor_id)
);

CREATE INDEX IF NOT EXISTS idx_doctor_master_name
ON doctor_master(doctor_name);

CREATE INDEX IF NOT EXISTS idx_doctor_shift_schedule_doctor
ON doctor_shift_schedule(doctor_id);

CREATE INDEX IF NOT EXISTS idx_doctor_time_slots_lookup
ON doctor_time_slots(doctor_id, weekday_name, shift_label, slot_start);
