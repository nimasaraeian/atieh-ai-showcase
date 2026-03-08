from pathlib import Path
import sys

p = Path(r".\scripts\bridge_1403_payment_appointment.py")
text = p.read_text(encoding="utf-8")
original = text

old = '''    c_name = _find_col(col_index, PAYMENT_NAME_HEADERS)
    c_phone = _find_col(col_index, PAYMENT_PHONE_HEADERS)'''

new = '''    c_name = _find_col(col_index, PAYMENT_NAME_HEADERS)

    # fallback: accept any column containing "نام بیمار"
    if not c_name:
        for c in df.columns:
            s = str(c).strip().replace("ي", "ی").replace("ك", "ک")
            if "نام بیمار" in s or "نام بيمار" in s:
                c_name = c
                break

    c_phone = _find_col(col_index, PAYMENT_PHONE_HEADERS)'''

if old not in text:
    print("ERROR: target block not found")
    sys.exit(1)

text = text.replace(old, new, 1)

if text == original:
    print("ERROR: no changes were applied")
    sys.exit(1)

p.write_text(text, encoding="utf-8")
print("PAYMENT NAME FALLBACK PATCH APPLIED")
