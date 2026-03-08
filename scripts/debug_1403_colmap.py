from pathlib import Path
import sys

repo = Path(r"C:\Users\USER\Documents\GitHub\atieh")
sys.path.insert(0, str(repo / "scripts"))

import bridge_1403_payment_appointment as m

pay_path = repo / "data" / "inputs" / "history" / "1403" / "payments_1403_full.xlsx"
appt_path = repo / "data" / "inputs" / "history" / "1403" / "نوبت_دهی_بیمارانی_که_حضور_پیدا_کردند_1403.xlsx"

df_pay, col_pay = m.load_payments(pay_path)
df_appt, col_appt = m.load_appointments(appt_path)

print("PAYMENT COL MAP:")
print(col_pay)
print()
print("APPOINTMENT COL MAP:")
print(col_appt)
