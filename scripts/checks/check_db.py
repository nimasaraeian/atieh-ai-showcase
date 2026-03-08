import sqlite3

c = sqlite3.connect("atieh_clinic.db")
cur = c.cursor()

print("patients =", cur.execute("select count(*) from patients").fetchone()[0])
print("appointments =", cur.execute("select count(*) from appointments").fetchone()[0])
print("payments(stg) =", cur.execute("select count(*) from stg_payments").fetchone()[0])
print("appt_errors(stg) =", cur.execute("select count(*) from stg_appointments where parse_status='error'").fetchone()[0])

c.close()
import sqlite3
from collections import Counter

DB = "atieh_clinic.db"
c = sqlite3.connect(DB)
cur = c.cursor()

# 1) basic availability checks
tables = ["patients", "appointments", "stg_payments"]
for t in tables:
    cur.execute(f"select count(*) from {t}")
    print(f"{t} rows =", cur.fetchone()[0])

# 2) sanity: payer_source_norm distribution
print("\n--- payer_source_norm distribution ---")
dist = cur.execute("""
    select payer_source_norm, count(*)
    from stg_payments
    group by payer_source_norm
    order by 2 desc
""").fetchall()
for r in dist:
    print(r)

# 3) pick 50 recent-ish payments and create a simple heuristic score
# (این فقط برای smoke تست است تا ببینیم داده‌ها قابل امتیازدهی هستند و خروجی مرتب می‌شود)
rows = cur.execute("""
    select
      payer_source_norm,
      coalesce(patient_share_pct, -1) as patient_share_pct,
      coalesce(insurer_name_norm, '') as insurer_name_norm
    from stg_payments
    limit 2000
""").fetchall()

def score(payer, pct, insurer):
    s = 0.0
    # insurance generally prioritized
    if payer == "insurance":
        s += 30
    elif payer == "cash":
        s += 10
    else:
        s -= 10

    # patient share: lower share => better coverage => slightly higher score
    if pct >= 0:
        s += max(0, 20 - (pct / 5))  # pct=0 => +20, pct=50 => +10, pct=100 => +0
    else:
        s -= 5

    # known insurers bonus (basic): frequent insurers get small bonus
    if insurer:
        s += 5

    return round(s, 2)

scored = [(score(p, pct, ins), p, pct, ins) for (p, pct, ins) in rows]
scored.sort(reverse=True, key=lambda x: x[0])

print("\n--- top 20 scored samples (smoke) ---")
for item in scored[:20]:
    print(item)

# 4) quick consistency checks
outliers = cur.execute("""
    select count(*)
    from stg_payments
    where patient_share_pct is not null and (patient_share_pct < 0 or patient_share_pct > 100)
""").fetchone()[0]
print("\npatient_share_pct outliers =", outliers)

c.close()