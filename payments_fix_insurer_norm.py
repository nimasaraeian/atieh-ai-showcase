import re
import sqlite3

def clean_insurer_name(name: str) -> str:
    if name is None:
        return None
    s = str(name).strip()

    # Normalize Arabic/Persian
    s = s.replace("ي", "ی").replace("ك", "ک")

    # Remove percent patterns anywhere (e.g., "ایران10%", "ایران 30 %", "البرز 20 درصد", "0%")
    s = re.sub(r"\s*\d+\s*%\s*", " ", s)
    s = re.sub(r"\s*\d+\s*درصد\s*", " ", s)

    # Some exports append numbers without percent (e.g., "بانک ملت 1")
    # Keep if it's part of the official name? In our case, clinic codes are irrelevant, so remove trailing standalone numbers.
    s = re.sub(r"\s+\d+\s*$", "", s)

    # Clean leftover symbols and spaces
    s = s.replace("%", " ")
    s = re.sub(r"\s+", " ", s).strip()

    return s

c = sqlite3.connect("atieh_clinic.db")
cur = c.cursor()

rows = cur.execute("""
SELECT DISTINCT insurer_name_norm
FROM stg_payments
WHERE insurer_name_norm IS NOT NULL
""").fetchall()

mapping = {}
for (old,) in rows:
    new = clean_insurer_name(old)
    if new and new != old:
        mapping[old] = new

print("distinct_to_change =", len(mapping))

updated = 0
for old, new in mapping.items():
    cur.execute("""
    UPDATE stg_payments
    SET insurer_name_norm = ?
    WHERE insurer_name_norm = ?
    """, (new, old))
    updated += cur.rowcount

c.commit()
print("updated_rows =", updated)

print("\n--- top insurers after cleanup ---")
top = cur.execute("""
SELECT insurer_name_norm, COUNT(1)
FROM stg_payments
GROUP BY insurer_name_norm
ORDER BY COUNT(1) DESC
LIMIT 25
""").fetchall()
for r in top:
    print(r)

c.close()