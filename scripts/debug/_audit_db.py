import sqlite3

c = sqlite3.connect('atieh_clinic.db')

tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
print("=== TABLE ROW COUNTS ===")
for t in tables:
    cnt = c.execute(f"SELECT COUNT(1) FROM [{t}]").fetchone()[0]
    print(f"  {t}: {cnt}")

print()
print("=== INDEXES ===")
idxs = c.execute("SELECT tbl_name, name, sql FROM sqlite_master WHERE type='index' ORDER BY tbl_name, name").fetchall()
for i in idxs:
    print(f"  [{i[0]}] {i[1]}")
    if i[2]:
        print(f"    SQL: {i[2][:120]}")

# Check for missing critical indexes
print()
print("=== COLUMN CHECK: appointments ===")
cols = [r[1] for r in c.execute("PRAGMA table_info(appointments)").fetchall()]
print("  columns:", cols)

print()
print("=== COLUMN CHECK: patients ===")
cols2 = [r[1] for r in c.execute("PRAGMA table_info(patients)").fetchall()]
print("  columns:", cols2)

print()
print("=== COLUMN CHECK: stg_appointments ===")
cols3 = [r[1] for r in c.execute("PRAGMA table_info(stg_appointments)").fetchall()]
print("  columns:", cols3)

print()
print("=== COLUMN CHECK: stg_payments ===")
cols4 = [r[1] for r in c.execute("PRAGMA table_info(stg_payments)").fetchall()]
print("  columns:", cols4[:20], "...total:", len(cols4))

print()
print("=== SCORING COLUMN NULLS IN appointments ===")
for col in ['patient_priority_score', 'insurance_score', 'treatment_score', 'tenure_score', 'frequency_score']:
    if col in cols:
        total = c.execute(f"SELECT COUNT(1) FROM appointments").fetchone()[0]
        nulls = c.execute(f"SELECT COUNT(1) FROM appointments WHERE [{col}] IS NULL").fetchone()[0]
        print(f"  {col}: {total - nulls}/{total} filled ({nulls} nulls)")

print()
print("=== ai_patient_scores table check ===")
has_cache = c.execute("SELECT COUNT(1) FROM sqlite_master WHERE type='table' AND name='ai_patient_scores'").fetchone()[0]
print(f"  ai_patient_scores exists: {bool(has_cache)}")

print()
print("=== stg_appointments parse_status distribution ===")
rows = c.execute("SELECT parse_status, COUNT(1) FROM stg_appointments GROUP BY parse_status").fetchall()
for r in rows:
    print(f"  {r[0]}: {r[1]}")

print()
print("=== appointments.payment_type distribution (raw) ===")
rows2 = c.execute("SELECT payment_type, COUNT(1) as n FROM appointments GROUP BY payment_type ORDER BY n DESC LIMIT 15").fetchall()
for r in rows2:
    print(f"  {repr(r[0])}: {r[1]}")

c.close()
