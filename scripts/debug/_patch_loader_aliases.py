from pathlib import Path
import re

p = Path(r".\scripts\load_payment_identity_staging.py")
text = p.read_text(encoding="utf-8")

pattern = r"def find_required_columns\(norm_headers\):.*?return found"
replacement = '''def find_required_columns(norm_headers):
    aliases = {
        "receipt_no": [
            "شماره رسید",
            "شماره رسيد",
        ],
        "record_no": [
            "شماره پرونده",
        ],
        "patient_name_raw": [
            "نام بیمار",
            "نام بيمار",
        ],
        "mobile_raw": [
            "موبایل",
            "موبايل",
        ],
        "national_id_raw": [
            "کد ملی",
            "كد ملي",
            "کد ملي",
        ],
        "admission_date_raw": [
            "تاریخ پذیرش",
            "تاريخ پذيرش",
        ],
        "net_received_raw": [
            "خالص دریافتی",
            "خالص دريافتي",
        ],
    }

    found = {}
    for key, options in aliases.items():
        idx = None
        for i, h in enumerate(norm_headers):
            if h in options:
                idx = i
                break
        found[key] = idx
    return found'''

new_text = re.sub(pattern, replacement, text, flags=re.DOTALL)
if new_text == text:
    raise SystemExit("ERROR: target function not found")

p.write_text(new_text, encoding="utf-8")
print("PATCH_APPLIED")
