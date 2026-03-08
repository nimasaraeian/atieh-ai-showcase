import sqlite3

DB = r".\atieh_clinic.db"

def normalize_spaces(s: str) -> str:
    return " ".join((s or "").strip().split())

def token_sort_name(s: str) -> str:
    s = normalize_spaces(s)
    if not s:
        return ""
    tokens = [t for t in s.split(" ") if t]
    tokens.sort()
    return " ".join(tokens)

conn = sqlite3.connect(DB)
cur = conn.cursor()

rows = cur.execute("""
    SELECT patient_id, name_norm
    FROM identity_patient_features
""").fetchall()

for patient_id, name_norm in rows:
    cur.execute("""
        UPDATE identity_patient_features
        SET name_token_sorted = ?
        WHERE patient_id = ?
    """, (token_sort_name(name_norm), patient_id))

rows = cur.execute("""
    SELECT record_no, name_norm
    FROM identity_record_features
""").fetchall()

for record_no, name_norm in rows:
    cur.execute("""
        UPDATE identity_record_features
        SET name_token_sorted = ?
        WHERE record_no = ?
    """, (token_sort_name(name_norm), record_no))

conn.commit()
conn.close()
print("token-sorted names updated successfully")
