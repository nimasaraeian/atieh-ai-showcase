from pathlib import Path
import re

p = Path(r".\scripts\bridge_1403_payment_appointment.py")
text = p.read_text(encoding="utf-8")

pattern = r"# Column candidates.*?APPT_PHONE_HEADERS = \[.*?\]\n"
replacement = """# Column candidates
PAYMENT_DATE_HEADERS = ["تاریخ پذیرش", "تاريخ پذيرش", "تاریخ", "تاريخ"]
PAYMENT_NAME_HEADERS = ["نام بیمار", "نام بيمار", "نام بیمار(تشکیل پرونده شده)"]
PAYMENT_PHONE_HEADERS = ["موبایل", "موبايل", "تلفن", "شماره تماس"]
PAYMENT_RECORDNO_HEADERS = ["شماره پرونده", "کد پرونده", "record_no", "پرونده"]

APPT_DATE_HEADERS = ["تاریخ نوبت", "تاريخ نوبت", "تاریخ", "تاريخ"]
APPT_NAME_HEADERS = [
    "نام بیمار(تشکیل پرونده شده)",
    "نام بيمار(تشكيل پرونده شده)",
    "نام و نام خانوادگی",
    "نام بیمار",
    "نام بيمار",
]
APPT_PHONE_HEADERS = ["موبایل", "موبايل", "تلفن", "شماره تماس", "تلفن همراه"]
"""

new_text, count = re.subn(pattern, replacement, text, flags=re.S)

if count != 1:
    raise SystemExit(f"ERROR: header block replacement failed, count={count}")

p.write_text(new_text, encoding="utf-8")
print("PATCHED HEADER CONSTANTS")
