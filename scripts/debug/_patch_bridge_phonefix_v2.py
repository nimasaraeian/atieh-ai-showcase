from pathlib import Path
import re
import sys

path = Path(r".\scripts\bridge_1404_payment_appointment.py")
text = path.read_text(encoding="utf-8")

original = text

# 1) Replace normalize_phones function by exact signature
pattern = re.compile(
    r"def normalize_phones\(raw: str \| None\) -> set\[str\]:\n(?:    .*\n)*?(?=\ndef )",
    re.MULTILINE
)

replacement = '''def normalize_phones(raw: str | None) -> set[str]:
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

    parts = re.split(r"[;،,/|\\s]+", raw)
    out: set[str] = set()

    for part in parts:
        token = str(part).strip()
        if not token:
            continue

        token = token.replace("\\u200c", "").replace("\\u200f", "").replace("\\ufeff", "")
        token = token.strip("[](){}<>\"'`")

        digits = "".join(ch for ch in token if ch.isdigit())

        if len(digits) == 11 and digits.startswith("09"):
            out.add(digits)

    return out
'''

text2, n = pattern.subn(replacement, text, count=1)
if n != 1:
    print("ERROR: normalize_phones exact replacement failed")
    sys.exit(1)

text = text2

# 2) Replace raw appointment phone with normalized one in all match dicts
text = text.replace('"appointment_phone": a.phone_raw,', '"appointment_phone": ";".join(sorted(a.phones)),')

# 3) Replace appointment_patient_key block
old = '''            first_phone = (m.get("appointment_phone") or "").strip()
            if first_phone and ";" in first_phone:
                first_phone = first_phone.split(";")[0].strip()
            m["appointment_patient_key"] = f"{m.get('appointment_name','')}|{m.get('appointment_date_key','')}|{first_phone}"'''

new = '''            normalized_appt_phone = ";".join(sorted(normalize_phones(m.get("appointment_phone") or "")))
            first_phone = normalized_appt_phone.split(";")[0].strip() if normalized_appt_phone else ""
            m["appointment_phone"] = normalized_appt_phone
            m["appointment_patient_key"] = f"{m.get('appointment_name','')}|{m.get('appointment_date_key','')}|{first_phone}"'''

if old in text:
    text = text.replace(old, new, 1)
else:
    text = re.sub(
        r'''            first_phone = \(m\.get\("appointment_phone"\) or ""\)\.strip\(\)\n            if first_phone and ";" in first_phone:\n                first_phone = first_phone\.split\(";"\)\[0\]\.strip\(\)\n            m\["appointment_patient_key"\] = f"\{m\.get\('appointment_name',''\)\}\|\{m\.get\('appointment_date_key',''\)\}\|\{first_phone\}"''',
        new,
        text,
        count=1,
    )

if text == original:
    print("WARNING: no changes were applied")
else:
    path.write_text(text, encoding="utf-8")
    print("PATCH APPLIED OK")
