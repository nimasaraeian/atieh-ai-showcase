# -*- coding: utf-8 -*-
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import pandas as pd
from pathlib import Path
REPO = Path(__file__).resolve().parent.parent
appt_dir = REPO / "data" / "inputs" / "history" / "1404"
appt_path = list(appt_dir.glob("*.xlsx"))[0]
df = pd.read_excel(appt_path, sheet_name=0, nrows=100)
out = []
out.append("Appointment columns: " + str([str(x) for x in df.columns]))
for c in df.columns:
    s = str(c)
    if "تلفن" in s or "موبا" in s or "phone" in s.lower():
        non_null = df[c].dropna()
        sample = repr(non_null.iloc[0]) if len(non_null) else "NONE"
        out.append("  Phone col: " + repr(c) + " non-null: " + str(len(non_null)) + " sample: " + sample)
(REPO / "data" / "outputs").mkdir(parents=True, exist_ok=True)
pay_path = REPO / "data" / "inputs" / "payments" / "payments_1404_full.xlsx"
df_pay = pd.read_excel(pay_path, sheet_name="MSExcel", nrows=100)
out.append("\nPayment columns: " + str([str(x) for x in df_pay.columns]))
for c in df_pay.columns:
    s = str(c)
    if "تلفن" in s or "موبا" in s or "phone" in s.lower() or "پرونده" in s:
        non_null = df_pay[c].dropna()
        sample = repr(non_null.iloc[0]) if len(non_null) else "NONE"
        out.append("  Col: " + repr(c) + " non-null: " + str(len(non_null)) + " sample: " + sample)
with open(REPO / "data" / "outputs" / "col_check.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
