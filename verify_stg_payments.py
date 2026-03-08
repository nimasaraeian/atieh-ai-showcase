"""Quick spot-check of stg_payments normalization. Writes to verify_out.txt."""
import sqlite3
from pathlib import Path

conn = sqlite3.connect(Path("atieh_clinic.db"))
cur  = conn.cursor()
lines = []

lines.append("-- Sample rows: insurer_raw -> insurer_name_norm / payer_source_norm / pct")
cur.execute("""
    SELECT insurer_raw, insurer_name_norm, payer_source_norm, patient_share_pct, pct_detected
    FROM stg_payments
    WHERE insurer_raw IS NOT NULL
    GROUP BY insurer_raw
    ORDER BY COUNT(*) DESC
    LIMIT 20
""")
for r in cur.fetchall():
    lines.append(f"  raw={repr(r[0])}  name={repr(r[1])}  src={r[2]}  pct={r[3]}  det={r[4]}")

lines.append("\n-- payer_source distribution:")
cur.execute("SELECT payer_source_norm, COUNT(*) FROM stg_payments GROUP BY payer_source_norm")
for r in cur.fetchall(): lines.append(f"  {r[0]}: {r[1]:,}")

conn.close()

with open("verify_out.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("Done - see verify_out.txt")
