from pathlib import Path

p = Path(r".\scripts\bridge_1403_payment_appointment.py")
text = p.read_text(encoding="utf-8")

target = "col_index = {_norm_header(c): c for c in df.columns}"

replacement = """
    # CLEAN HEADER NAMES (remove quotes + normalize Persian letters)
    df.columns = [
        str(c)
        .replace("'", "")
        .replace('"', "")
        .strip()
        .replace("ي","ی")
        .replace("ك","ک")
        for c in df.columns
    ]

    col_index = {_norm_header(c): c for c in df.columns}
"""

text = text.replace(target, replacement)

p.write_text(text, encoding="utf-8")
print("HEADER CLEANUP PATCH APPLIED")
