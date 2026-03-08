from pathlib import Path
import re
import sys

path = Path(r".\scripts\bridge_1404_payment_appointment.py")
text = path.read_text(encoding="utf-8")

original = text

# -------------------------------------------------
# Ensure import re exists
# -------------------------------------------------
if "import re" not in text:
    if "import sqlite3" in text:
        text = text.replace("import sqlite3", "import sqlite3\nimport re", 1)
    else:
        text = "import re\n" + text

# -------------------------------------------------
# Replace normalize_phones(...) with a strict version
# -------------------------------------------------
pattern_func = re.compile(
    r"def normalize_phones\([^\)]*\):\n(?:    .*\n)+?(?=\ndef |\n@class |\nif __name__ == ['\"]__main__['\"]:)",
    re.MULTILINE
)

replacement_func = '''def normalize_phones(raw_value) -> set[str]:
    """
    Normalize a phone cell into a clean set of valid Iranian mobile numbers.

    Rules:
    - split on ; ، , / | and whitespace/newlines
    - keep only tokens matching 09xxxxxxxxx
    - drop junk like 0, 1, short numbers, text, treatment labels
    - deduplicate automatically via set
    """
    if raw_value is None:
        return set()

    raw = str(raw_value).strip()
    if not raw:
        return set()

    parts = re.split(r"[;،,/|\\s]+", raw)
    out = set()

    for part in parts:
        token = str(part).strip()

        if not token:
            continue

        # remove invisible/control chars and common wrappers
        token = token.replace("\\u200c", "").replace("\\u200f", "").replace("\\ufeff", "")
        token = token.strip("[](){}<>\"'`")

        # keep digits only for validation
        digits = "".join(ch for ch in token if ch.isdigit())

        # only valid Iranian mobile numbers: 09 + 9 digits
        if len(digits) == 11 and digits.startswith("09"):
            out.add(digits)

    return out
'''

m = pattern_func.search(text)
if not m:
    print("ERROR: normalize_phones function not found")
    sys.exit(1)

text = text[:m.start()] + replacement_func + text[m.end():]

# -------------------------------------------------
# Store normalized appointment phones in accepted matches
# -------------------------------------------------
text = text.replace('"appointment_phone": a.phone_raw,', '"appointment_phone": ";".join(sorted(a.phones)),')
text = text.replace('"appointment_phone": a.phone_raw,', '"appointment_phone": ";".join(sorted(a.phones)),')
text = text.replace('"appointment_phone": a.phone_raw,', '"appointment_phone": ";".join(sorted(a.phones)),')

# -------------------------------------------------
# Build appointment_patient_key from normalized phone, not raw phone
# -------------------------------------------------
old_block = """            first_phone = (m.get("appointment_phone") or "").strip()
            if first_phone and ";" in first_phone:
                first_phone = first_phone.split(";")[0].strip()
            m["appointment_patient_key"] = f"{m.get('appointment_name','')}|{m.get('appointment_date_key','')}|{first_phone}" """

new_block = """            normalized_appt_phone = ";".join(sorted(normalize_phones(m.get("appointment_phone") or "")))
            first_phone = normalized_appt_phone.split(";")[0].strip() if normalized_appt_phone else ""
            m["appointment_phone"] = normalized_appt_phone
            m["appointment_patient_key"] = f"{m.get('appointment_name','')}|{m.get('appointment_date_key','')}|{first_phone}" """

if old_block not in text:
    # fallback regex replacement
    text = re.sub(
        r"""            first_phone = \(m\.get\("appointment_phone"\) or ""\)\.strip\(\)\n            if first_phone and ";" in first_phone:\n                first_phone = first_phone\.split\(";"\)\[0\]\.strip\(\)\n            m\["appointment_patient_key"\] = f"\{m\.get\('appointment_name',''\)\}\|\{m\.get\('appointment_date_key',''\)\}\|\{first_phone\}" """,
        new_block,
        text
    )
else:
    text = text.replace(old_block, new_block, 1)

if text == original:
    print("WARNING: no changes were applied")
else:
    path.write_text(text, encoding="utf-8")
    print("PATCH APPLIED OK")
