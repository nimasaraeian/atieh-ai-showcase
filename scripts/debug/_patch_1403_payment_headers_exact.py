from pathlib import Path
import sys

p = Path(r".\scripts\bridge_1403_payment_appointment.py")
text = p.read_text(encoding="utf-8")
original = text

old = '        df = pd.read_excel(path, sheet_name=0, engine="openpyxl", dtype=str)' + "\n" + '    col_index = {_norm_header(c): c for c in df.columns}'
new = '''        df = pd.read_excel(path, sheet_name=0, engine="openpyxl", dtype=str)
        df.columns = [
            str(c).strip().strip("'").strip('"').replace("ي", "ی").replace("ك", "ک")
            for c in df.columns
        ]
    col_index = {_norm_header(c): c for c in df.columns}'''

if old not in text:
    print("ERROR: target block not found")
    sys.exit(1)

text = text.replace(old, new, 1)

if text == original:
    print("ERROR: no changes were applied")
    sys.exit(1)

p.write_text(text, encoding="utf-8")
print("1403 PAYMENT HEADER CLEANUP PATCH APPLIED")
