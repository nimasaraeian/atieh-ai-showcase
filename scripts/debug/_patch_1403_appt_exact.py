from pathlib import Path
import sys

p = Path(r".\scripts\bridge_1403_payment_appointment.py")
text = p.read_text(encoding="utf-8")
original = text

old = '''    c_date = _find_col(col_index, APPT_DATE_HEADERS)
    c_name = _find_col(col_index, APPT_NAME_HEADERS)
    c_phone = _find_col(col_index, APPT_PHONE_HEADERS)'''

new = '''    c_date = _find_col(col_index, APPT_DATE_HEADERS)
    c_name = _find_col(col_index, APPT_NAME_HEADERS)

    # fallback for 1403 appointment files
    if not c_name:
        preferred = [
            "نام بیمار(تشکیل پرونده شده)",
            "نام بیمار (تشکیل پرونده شده)",
            "نام بیمار(تشکیل پرونده نشده)",
            "نام بیمار (تشکیل پرونده نشده)",
            "نام بیمار",
            "نام بيمار",
        ]
        cols_norm = {
            str(c).strip().replace("ي", "ی").replace("ك", "ک"): c
            for c in df.columns
        }

        for key in preferred:
            k = key.strip().replace("ي", "ی").replace("ك", "ک")
            if k in cols_norm:
                c_name = cols_norm[k]
                break

        if not c_name:
            for c in df.columns:
                s = str(c).strip().replace("ي", "ی").replace("ك", "ک")
                if "نام بیمار" in s or "نام بيمار" in s:
                    c_name = c
                    break

    c_phone = _find_col(col_index, APPT_PHONE_HEADERS)'''

if old not in text:
    print("ERROR: exact appointment block not found")
    sys.exit(1)

text = text.replace(old, new, 1)

if text == original:
    print("ERROR: no changes were applied")
    sys.exit(1)

p.write_text(text, encoding="utf-8")
print("APPOINTMENT NAME FALLBACK PATCH APPLIED")
