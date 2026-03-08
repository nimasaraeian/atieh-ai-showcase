import sqlite3

c = sqlite3.connect("atieh_clinic.db")
cur = c.cursor()

cols = [r[1] for r in cur.execute("PRAGMA table_info(stg_payments)").fetchall()]
print("stg_payments columns contain:")
for k in ["payer_source_norm", "insurer_name_norm", "patient_share_pct", "insurer_raw"]:
    print(f"  {k} =", (k in cols))

def show(title, q):
    print("\n" + title)
    for row in cur.execute(q).fetchall():
        print(row)

if "payer_source_norm" in cols:
    show("--- payer_source_norm distribution ---", """
    SELECT payer_source_norm, COUNT(1)
    FROM stg_payments
    GROUP BY payer_source_norm
    ORDER BY COUNT(1) DESC
    """)

if "insurer_name_norm" in cols:
    show("--- top insurers (norm) ---", """
    SELECT insurer_name_norm, COUNT(1)
    FROM stg_payments
    GROUP BY insurer_name_norm
    ORDER BY COUNT(1) DESC
    LIMIT 25
    """)

if "patient_share_pct" in cols:
    show("--- patient_share_pct distribution (top) ---", """
    SELECT patient_share_pct, COUNT(1)
    FROM stg_payments
    GROUP BY patient_share_pct
    ORDER BY COUNT(1) DESC
    LIMIT 20
    """)

# sanity: how many insurance rows have NULL pct (should be 0 if defaulting works)
if "payer_source_norm" in cols and "patient_share_pct" in cols:
    show("--- insurance rows with NULL pct (should be 0) ---", """
    SELECT COUNT(1)
    FROM stg_payments
    WHERE payer_source_norm='insurance' AND patient_share_pct IS NULL
    """)

c.close()