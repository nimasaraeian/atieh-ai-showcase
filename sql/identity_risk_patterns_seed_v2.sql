BEGIN;

INSERT INTO identity_name_risk_patterns (pattern_a, pattern_b, risk_level, notes)
SELECT 'حمید','حمیده','HIGH','male/female similar names'
WHERE NOT EXISTS (
    SELECT 1 FROM identity_name_risk_patterns
    WHERE pattern_a='حمید' AND pattern_b='حمیده'
);

INSERT INTO identity_name_risk_patterns (pattern_a, pattern_b, risk_level, notes)
SELECT 'حسن','حسین','HIGH','similar Persian names'
WHERE NOT EXISTS (
    SELECT 1 FROM identity_name_risk_patterns
    WHERE pattern_a='حسن' AND pattern_b='حسین'
);

INSERT INTO identity_name_risk_patterns (pattern_a, pattern_b, risk_level, notes)
SELECT 'مهدی','مهدیه','HIGH','male/female similar names'
WHERE NOT EXISTS (
    SELECT 1 FROM identity_name_risk_patterns
    WHERE pattern_a='مهدی' AND pattern_b='مهدیه'
);

INSERT INTO identity_name_risk_patterns (pattern_a, pattern_b, risk_level, notes)
SELECT 'رضا','راضیه','HIGH','male/female similar names'
WHERE NOT EXISTS (
    SELECT 1 FROM identity_name_risk_patterns
    WHERE pattern_a='رضا' AND pattern_b='راضیه'
);

INSERT INTO identity_name_risk_patterns (pattern_a, pattern_b, risk_level, notes)
SELECT 'امین','امیر','MEDIUM','close names'
WHERE NOT EXISTS (
    SELECT 1 FROM identity_name_risk_patterns
    WHERE pattern_a='امین' AND pattern_b='امیر'
);

INSERT INTO identity_name_risk_patterns (pattern_a, pattern_b, risk_level, notes)
SELECT 'احد','احمد','HIGH','close names'
WHERE NOT EXISTS (
    SELECT 1 FROM identity_name_risk_patterns
    WHERE pattern_a='احد' AND pattern_b='احمد'
);

COMMIT;
