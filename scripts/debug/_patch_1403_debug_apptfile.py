from pathlib import Path
import sys

p = Path(r".\scripts\bridge_1403_payment_appointment.py")
text = p.read_text(encoding="utf-8")
original = text

old = """    if not appt_path.exists() and appt_dir.exists():
        candidates = sorted(appt_dir.glob("*.xlsx"))
        if candidates:
            appt_path = candidates[0]"""

new = """    if not appt_path.exists() and appt_dir.exists():
        candidates = sorted(appt_dir.glob("*.xlsx"))
        if candidates:
            appt_path = candidates[0]
            print(f"  [DEBUG] selected appointment file: {appt_path}")"""

if old not in text:
    print("ERROR: fallback block not found")
    sys.exit(1)

text = text.replace(old, new, 1)

if text == original:
    print("ERROR: no changes were applied")
    sys.exit(1)

p.write_text(text, encoding="utf-8")
print("DEBUG PATCH APPLIED")
