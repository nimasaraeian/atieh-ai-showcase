from pathlib import Path

p = Path(r".\scripts\bridge_1403_payment_appointment.py")
text = p.read_text(encoding="utf-8")

old = "df.columns = ["
insert = '''
    # normalize Persian headers like: نام بیمار(تشکیل پرونده شده)
    df.columns = [
        str(c).replace("نام بيمار(تشکیل پرونده شده)", "نام بيمار")
        .replace("نام بیمار(تشکیل پرونده شده)", "نام بیمار")
        for c in df.columns
    ]

'''

if old in text:
    text = text.replace(old, insert + old, 1)

p.write_text(text, encoding="utf-8")
print("HEADER NORMALIZATION PATCHED")
