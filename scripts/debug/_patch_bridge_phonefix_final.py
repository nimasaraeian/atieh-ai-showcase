from pathlib import Path
import sys

path = Path(r".\scripts\bridge_1404_payment_appointment.py")
text = path.read_text(encoding="utf-8")
original = text

# --------------------------------------
# 1) Safe bounded replace: normalize_phones only
# --------------------------------------
start_marker = "def normalize_phones(raw: str | None) -> set[str]:"
end_marker = "\ndef normalize_date_key(val) -> str | None:"

start = text.find(start_marker)
if start == -1:
    print("ERROR: normalize_phones start marker not found")
    sys.exit(1)

end = text.find(end_marker, start)
if end == -1:
    print("ERROR: normalize_date_key marker not found")
    sys.exit(1)

new_func = '''def normalize_phones(raw: str | None) -> set[str]:
    """
    Split phone-like cells into a clean set of valid Iranian mobile numbers.

    Keep only:
    - 11 digits
    - starts with 09

    Supports common variants:
    - +98xxxxxxxxxx
    - 98xxxxxxxxxx
    - 9xxxxxxxxx
    - 09xxxxxxxxx

    Drops junk like:
    - 0 / 1
    - short numbers
    - treatment text
    - mixed notes
    """
    out = set()
    if not raw or (isinstance(raw, float) and pd.isna(raw)):
        return out

    s = str(raw).strip()
    if not s:
        return out

    s = _normalize_digits(s)

    # split on common separators
    parts = re.split(r"[;،,/|\\s]+", s)

    for p in parts:
        token = str(p).strip()
        if not token:
            continue

        digits = "".join(c for c in token if c.isdigit())
        if not digits:
            continue

        # convert +98 / 98 prefix to local mobile format
        if digits.startswith("98") and len(digits) >= 12:
            digits = "0" + digits[2:]

        # convert 9xxxxxxxxx to 09xxxxxxxxx
        if len(digits) == 10 and digits.startswith("9"):
            digits = "0" + digits

        # keep ONLY strict valid mobile numbers
        if len(digits) == 11 and digits.startswith("09"):
            out.add(digits)

    return out

'''

text = text[:start] + new_func + text[end:]

# --------------------------------------
# 2) Safe exact replace: store normalized appointment_phone
# --------------------------------------
raw_phone_pattern = '"appointment_phone": a.phone_raw,'
raw_count_before = text.count(raw_phone_pattern)
text = text.replace(raw_phone_pattern, '"appointment_phone": ";".join(sorted(a.phones)),')
raw_count_after = text.count(raw_phone_pattern)

# --------------------------------------
# 3) Safe exact replace: appointment_patient_key block
# --------------------------------------
old_block = '''            first_phone = (m.get("appointment_phone") or "").strip()
            if first_phone and ";" in first_phone:
                first_phone = first_phone.split(";")[0].strip()
            m["appointment_patient_key"] = f"{m.get('appointment_name','')}|{m.get('appointment_date_key','')}|{first_phone}"'''

new_block = '''            normalized_appt_phone = ";".join(sorted(normalize_phones(m.get("appointment_phone") or "")))
            first_phone = normalized_appt_phone.split(";")[0].strip() if normalized_appt_phone else ""
            m["appointment_phone"] = normalized_appt_phone
            m["appointment_patient_key"] = f"{m.get('appointment_name','')}|{m.get('appointment_date_key','')}|{first_phone}"'''

if old_block not in text:
    print("ERROR: appointment_patient_key block not found")
    sys.exit(1)

text = text.replace(old_block, new_block, 1)

if text == original:
    print("ERROR: no changes were applied")
    sys.exit(1)

path.write_text(text, encoding="utf-8")
print("PATCH APPLIED OK")
print(f"normalize_phones replaced: yes")
print(f"appointment_phone replacements: {raw_count_before - raw_count_after}")
print(f"normalized_appt_phone inserted: {'normalized_appt_phone' in text}")
