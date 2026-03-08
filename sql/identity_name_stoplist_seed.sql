BEGIN;

CREATE TABLE IF NOT EXISTS identity_name_stoplist (
    stop_id INTEGER PRIMARY KEY AUTOINCREMENT,
    stop_pattern TEXT NOT NULL,
    stop_reason TEXT
);

INSERT INTO identity_name_stoplist (stop_pattern, stop_reason)
SELECT 'دندانپزشکی', 'generic organization label'
WHERE NOT EXISTS (
    SELECT 1 FROM identity_name_stoplist WHERE stop_pattern = 'دندانپزشکی'
);

INSERT INTO identity_name_stoplist (stop_pattern, stop_reason)
SELECT 'کلینیک', 'generic organization label'
WHERE NOT EXISTS (
    SELECT 1 FROM identity_name_stoplist WHERE stop_pattern = 'کلینیک'
);

INSERT INTO identity_name_stoplist (stop_pattern, stop_reason)
SELECT 'مطب', 'generic organization label'
WHERE NOT EXISTS (
    SELECT 1 FROM identity_name_stoplist WHERE stop_pattern = 'مطب'
);

INSERT INTO identity_name_stoplist (stop_pattern, stop_reason)
SELECT 'بیمارستان', 'generic organization label'
WHERE NOT EXISTS (
    SELECT 1 FROM identity_name_stoplist WHERE stop_pattern = 'بیمارستان'
);

INSERT INTO identity_name_stoplist (stop_pattern, stop_reason)
SELECT 'درمانگاه', 'generic organization label'
WHERE NOT EXISTS (
    SELECT 1 FROM identity_name_stoplist WHERE stop_pattern = 'درمانگاه'
);

COMMIT;
