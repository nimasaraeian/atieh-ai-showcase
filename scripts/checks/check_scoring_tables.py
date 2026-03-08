import sqlite3, os

p = os.path.abspath("atieh_clinic.db")
print("DB PATH:", p)

conn = sqlite3.connect(p)
cur = conn.cursor()

def safe(q):
    try:
        return cur.execute(q).fetchall()
    except Exception as e:
        return f"ERROR: {e}"

print("\npatient_financial_summary count:", safe("SELECT COUNT(1) FROM patient_financial_summary"))
print("patient_financial_summary sample:", safe("SELECT * FROM patient_financial_summary LIMIT 3"))

print("\nfinancial_patient_dim count:", safe("SELECT COUNT(1) FROM financial_patient_dim"))
print("financial_patient_dim sample:", safe("SELECT * FROM financial_patient_dim LIMIT 3"))

conn.close()
