from pathlib import Path

p = Path(r".\scripts\bridge_1403_payment_appointment.py")
text = p.read_text(encoding="utf-8")

original = text

helper = """
def _clean_colname(x):
    s = str(x).strip()
    if s.startswith("'") and s.endswith("'") and len(s) >= 2:
        s = s[1:-1].strip()
    s = s.replace("ي", "ی").replace("ك", "ک")
    s = " ".join(s.split())
    return s

def _clean_columns(df):
    df = df.copy()
    df.columns = [_clean_colname(c) for c in df.columns]
    return df
"""

if "def _clean_colname(x):" not in text:
    marker = "REPO = Path(__file__).resolve().parents[1]"
    if marker in text:
        text = text.replace(marker, marker + "\n\n" + helper)
    else:
        raise SystemExit("ERROR: marker for inserting helper not found")

text = text.replace(
    "df = pd.read_excel(path)",
    "df = pd.read_excel(path)\n    df = _clean_columns(df)"
)

text = text.replace(
    "df = pd.read_excel(path, sheet_name=sheet_name)",
    "df = pd.read_excel(path, sheet_name=sheet_name)\n    df = _clean_columns(df)"
)

if text == original:
    raise SystemExit("ERROR: no changes applied")

p.write_text(text, encoding="utf-8")
print("PATCH APPLIED")
