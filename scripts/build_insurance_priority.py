from pathlib import Path
import json
import re
import pandas as pd

ROOT = Path(".")
SRC = ROOT / "data" / "inputs" / "reference" / "تاریخ پرداختی بیمه ها.xlsx"
OUT_DIR = ROOT / "data" / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON = OUT_DIR / "insurance_priority.json"

GROUP_SCORE = {
    "یک ماه": 0.90,
    "دو ماه": 0.75,
    "سه ماه": 0.60,
    "چهار ماه": 0.45,
    "بیشتر از 5 ماه": 0.25,
}

def norm_text(value):
    s = str(value or "").strip()
    s = s.replace("ي", "ی").replace("ك", "ک")
    s = s.replace("‌", " ")
    s = s.replace("\n", " ").replace("\r", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def normalize_insurance_name(name: str) -> str:
    s = norm_text(name)
    s = s.replace("بیمه", "").strip()
    s = re.sub(r"\d+\s*%", "", s)
    s = re.sub(r"\d+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

if not SRC.exists():
    raise SystemExit(f"Reference file not found: {SRC}")

df = pd.read_excel(SRC, header=1)
df.columns = [norm_text(c) for c in df.columns]

needed_cols = ["نام بیمه", "یک ماه", "دو ماه", "سه ماه", "چهار ماه", "بیشتر از 5 ماه"]
missing = [c for c in needed_cols if c not in df.columns]
if missing:
    print("Detected columns:", df.columns.tolist())
    raise SystemExit(f"Missing columns in Excel: {missing}")

rows = []
for _, row in df.iterrows():
    insurance_name = normalize_insurance_name(row.get("نام بیمه"))
    if not insurance_name:
        continue

    payment_group = None
    for col in ["یک ماه", "دو ماه", "سه ماه", "چهار ماه", "بیشتر از 5 ماه"]:
        cell = row.get(col)
        if pd.notna(cell) and str(cell).strip() in ["*", "＊", "★"]:
            payment_group = col
            break

    if payment_group is None:
        continue

    rows.append({
        "insurance_name": insurance_name,
        "payment_speed_group": payment_group,
        "priority_score": GROUP_SCORE[payment_group]
    })

rows.sort(key=lambda x: (-x["priority_score"], x["insurance_name"]))

payload = {
    "source_file": str(SRC),
    "excel_header_row": 1,
    "cash_priority_score": 1.00,
    "cash_rank_note": "CASH is always highest priority in scheduling decisions.",
    "items": rows
}

OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Wrote: {OUT_JSON}")
print(f"Items: {len(rows)}")
