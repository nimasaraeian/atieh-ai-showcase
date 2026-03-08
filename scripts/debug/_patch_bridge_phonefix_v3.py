from pathlib import Path
import sys

path = Path(r".\scripts\bridge_1404_payment_appointment.py")
text = path.read_text(encoding="utf-8")
original = text

# -------------------------------------------------
# 1) Replace normalize_phones by exact text block slicing
# -------------------------------------------------
func_start = text.find("def normalize_phones(raw: str | None) -> set[str]:")
if func_start == -1:
    print("ERROR: normalize_phones function start not found")
    sys.exit(1)

func_end = text.find("\ndef build_pay_rows(", func_start)
if func_end == -1:
    print("ERROR: normalize_phones function end marker not found")
    sys.exit(1)

new_func = '''def normalize_phones(raw: str | None) -> set[str]:
    """
    Return a clean set of valid Iranian mobile numbers from a dirty cell.

    Rules:
    - split on ; ، , / | whitespace
    - keep only 11-digit mobile numbers starting with 09
    - drop junk like 0, 1, short numbers, notes, treatment text
    """
    if raw is None:
        return set()

    raw = str(raw).strip()
    if not raw:
        return set()

    import re
    parts = re.split(r"[;،,/|\\s]+", raw)
    out: set[str] = set()

    for part in parts:
        token = str(part).strip()
        if not token:
            continue

        token = token.replace("\\u200c", "").replace("\\u200f", "").replace("\\ufeff", "")
        token = token.strip("[](){}<>\\"'`")

        digits = "".join(ch for ch in token if ch.isdigit())

        if len(digits) == 11 and digits.startswith("09"):
            out.add(digits)

    return out
'''

text = text[:func_start] + new_func + text[func_end:]

# -------------------------------------------------
# 2) Replace raw appointment phone with normalized one
# -------------------------------------------------
count_before = text.count('"appointment_phone": a.phone_raw,')
text = text.replace('"appointment_phone": a.phone_raw,', '"appointment_phone": ";".join(sorted(a.phones)),')
count_after = text.count('"appointment_phone": a.phone_raw,')

# -------------------------------------------------
# 3) Replace appointment_patient_key block by exact string replace
# -------------------------------------------------
old_block = '''            first_phone = (m.get("appointment_phone") or "").strip()
            if first_phone and ";" in first_phone:
                first_phone = first_phone.split(";")[0].strip()
            m["appointment_patient_key"] = f"{m.get('appointment_name','')}|{m.get('appointment_date_key','')}|{first_phone}"'''

new_block = '''            normalized_appt_phone = ";".join(sorted(normalize_phones(m.get("appointment_phone") or "")))
            first_phone = normalized_appt_phone.split(";")[0].strip() if normalized_appt_phone else ""
            m["appointment_phone"] = normalized_appt_phone
            m["appointment_patient_key"] = f"{m.get('appointment_name','')}|{m.get('appointment_date_key','')}|{first_phone}"'''

if old_block in text:
    text = text.replace(old_block, new_block, 1)
else:
    print("ERROR: appointment_patient_key block not found")
    sys.exit(1)

if text == original:
    print("WARNING: no changes were applied")
    sys.exit(1)

path.write_text(text, encoding="utf-8")
print("PATCH APPLIED OK")
print(f"Replaced raw appointment_phone occurrences: {count_before - count_after}")
