# -*- coding: utf-8 -*-
"""
تحلیل کامل فایل اکسل payments_1403_full.xlsx
- ساختار شیت‌ها و ستون‌ها
- شماره تلفن، کد ملی، خالص دریافتی و سایر ستون‌های مهم
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
XLSX_PATH = REPO / "data" / "inputs" / "payments" / "payments_1403_full.xlsx"


def _norm_header(s) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    t = str(s).strip()
    t = t.replace("|", " ").replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")
    return " ".join(t.split())


def _safe_str(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val).strip()


def _to_num(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip().replace(",", "").replace("،", "")
    if not s or s in ("-", "—", "nan"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


# نام‌های ممکن برای هر نوع ستون
PHONE_HEADERS = ["موبایل", "موبايل", "تلفن", "شماره تماس", "تلفن همراه", "همراه"]
NATIONAL_ID_HEADERS = ["کد ملی", "كد ملي", "کد ملي", "کدملی", "شناسه ملی"]
NET_RECEIVED_HEADERS = ["خالص دریافتی", "خالص دريافتي", "خالص دريافتی"]
PATIENT_NAME_HEADERS = ["نام بیمار", "نام بيمار", "نام بیمار(تشکیل پرونده شده)"]
RECORD_NO_HEADERS = ["شماره پرونده", "کد پرونده", "شماره پرونده"]
DATE_HEADERS = ["تاریخ پذیرش", "تاريخ پذيرش", "تاریخ"]
PATIENT_SHARE_HEADERS = ["سهم بیمار", "سهم بيمار"]
INSURER_SHARE_HEADERS = ["سهم سازمان", "سهم سازمان"]
INSURER_HEADERS = ["سازمان بیمه گر بیمار", "سازمان |بيمه گر بيمار", "بیمه گر", "سازمان بيمه گر", "سازمان |بیمه گر بیمار"]


def find_column(col_index_norm: dict, candidates: list) -> str | None:
    for c in candidates:
        if c in col_index_norm:
            return col_index_norm[c]
    for c in candidates:
        for k in col_index_norm:
            if c in k or k in c:
                return col_index_norm[k]
    return None


def analyze_phones(series: pd.Series) -> dict:
    """تحلیل ستون تلفن: تعداد پر، خالی، نمونه، تعداد موبایل معتبر ۰۹xxxxxxxxx"""
    total = len(series)
    non_empty = series.dropna().astype(str).str.strip()
    non_empty = non_empty[non_empty != ""]
    filled = len(non_empty)
    # موبایل معتبر: ۱۱ رقم، با ۰۹
    def is_valid_mobile(s):
        s = str(s).strip()
        s = re.sub(r"^\+98", "0", s)
        s = re.sub(r"^98", "0", s)
        s = "".join(c for c in s if c.isdigit())
        return len(s) == 11 and s.startswith("09") if s else False
    valid = sum(1 for v in non_empty if is_valid_mobile(v))
    samples = non_empty.head(10).tolist()
    return {
        "total": total,
        "filled": filled,
        "empty": total - filled,
        "valid_09_mobile": valid,
        "samples": samples,
    }


def analyze_national_id(series: pd.Series) -> dict:
    """تحلیل ستون کد ملی: ۱۰ رقم، نمونه"""
    total = len(series)
    non_empty = series.dropna().astype(str).str.strip()
    non_empty = non_empty[non_empty != ""]
    filled = len(non_empty)
    digits_only = non_empty.str.replace(r"\D", "", regex=True)
    valid_10 = (digits_only.str.len() == 10).sum()
    samples = non_empty.head(10).tolist()
    return {
        "total": total,
        "filled": filled,
        "empty": total - filled,
        "valid_10_digit": int(valid_10),
        "samples": samples,
    }


def analyze_net_received(series: pd.Series) -> dict:
    """تحلیل خالص دریافتی: عدد، جمع، min/max، توزیع"""
    total = len(series)
    values = []
    for v in series:
        n = _to_num(v)
        if n is not None:
            values.append(n)
    filled = len(values)
    if not values:
        return {"total": total, "filled": 0, "empty": total, "sum": 0, "min": None, "max": None, "samples": []}
    return {
        "total": total,
        "filled": filled,
        "empty": total - filled,
        "sum": sum(values),
        "min": min(values),
        "max": max(values),
        "samples": values[:10],
    }


def main():
    if not XLSX_PATH.exists():
        print(f"فایل یافت نشد: {XLSX_PATH}")
        return 1

    lines = []
    def out(s: str = ""):
        lines.append(s)
        print(s)

    out("# گزارش کامل فایل اکسل payments_1403_full.xlsx")
    out()
    out("## ۱. اطلاعات فایل و شیت‌ها")
    out()

    xl = pd.ExcelFile(XLSX_PATH, engine="openpyxl")
    sheet_names = xl.sheet_names
    out(f"- تعداد شیت‌ها: **{len(sheet_names)}**")
    out(f"- نام شیت‌ها: {', '.join(sheet_names)}")
    out()

    # ابعاد هر شیت
    for name in sheet_names:
        df = pd.read_excel(XLSX_PATH, sheet_name=name, engine="openpyxl", dtype=str, header=0)
        out(f"- شیت **{name}**: {len(df)} سطر، {len(df.columns)} ستون")
    out()

    # شیت اصلی: خواندن ۲۰۰۰ سطر اول برای سرعت (فایل ~۵۰ مگ)
    SAMPLE_ROWS = 2_000
    df = pd.read_excel(XLSX_PATH, sheet_name=0, engine="openpyxl", dtype=str, nrows=SAMPLE_ROWS + 1)
    total_rows = len(df)
    total_cols = len(df.columns)
    sample_note = "" if total_rows <= SAMPLE_ROWS else f" (آمار و نمونه‌ها بر اساس {SAMPLE_ROWS} سطر اول از فایل؛ تعداد سطرهای بارگذاری‌شده: {total_rows})"

    out("## ۲. ستون‌های شیت اول (هدر)")
    out()
    col_index_raw = list(df.columns)
    col_index_norm = {_norm_header(c): c for c in df.columns}
    out("| # | نام اصلی ستون | نام نرمال‌شده |")
    out("|---|----------------|---------------|")
    for i, (raw, norm) in enumerate(zip(col_index_raw, [_norm_header(c) for c in col_index_raw]), 1):
        raw_display = (str(raw)[:40] + "…") if len(str(raw)) > 40 else str(raw)
        norm_display = (norm[:35] + "…") if len(norm) > 35 else norm
        out(f"| {i} | {raw_display} | {norm_display} |")
    out()

    out("## ۳. شناسایی ستون‌های کلیدی")
    out()

    found = {}
    found["phone"] = find_column(col_index_norm, PHONE_HEADERS)
    found["national_id"] = find_column(col_index_norm, NATIONAL_ID_HEADERS)
    found["net_received"] = find_column(col_index_norm, NET_RECEIVED_HEADERS)
    found["patient_name"] = find_column(col_index_norm, PATIENT_NAME_HEADERS)
    found["record_no"] = find_column(col_index_norm, RECORD_NO_HEADERS)
    found["date"] = find_column(col_index_norm, DATE_HEADERS)
    found["patient_share"] = find_column(col_index_norm, PATIENT_SHARE_HEADERS)
    found["insurer_share"] = find_column(col_index_norm, INSURER_SHARE_HEADERS)
    found["insurer"] = find_column(col_index_norm, INSURER_HEADERS)

    for key, col in found.items():
        status = col if col else "— یافت نشد"
        out(f"- **{key}**: {status}")
    out()

    out("## ۴. آمار کلی شیت اول")
    out()
    out(f"- تعداد سطرهای بارگذاری‌شده: **{total_rows}**{sample_note}")
    out(f"- تعداد ستون‌ها: **{total_cols}**")
    out()

    out("## ۵. تحلیل ستون تلفن (موبایل)")
    out()
    if found["phone"]:
        col = found["phone"]
        ser = df[col]
        res = analyze_phones(ser)
        out(f"- نام ستون: `{col}`")
        out(f"- تعداد کل سطرها: {res['total']}")
        out(f"- پر (غیر خالی): {res['filled']}")
        out(f"- خالی: {res['empty']}")
        out(f"- موبایل معتبر (۱۱ رقم، شروع با ۰۹): {res['valid_09_mobile']}")
        out("- نمونه مقادیر:")
        for s in res["samples"][:8]:
            out(f"  - `{s}`")
    else:
        out("ستون تلفن با نام‌های متداول یافت نشد.")
    out()

    out("## ۶. تحلیل ستون کد ملی")
    out()
    if found["national_id"]:
        col = found["national_id"]
        ser = df[col]
        res = analyze_national_id(ser)
        out(f"- نام ستون: `{col}`")
        out(f"- تعداد کل: {res['total']}")
        out(f"- پر: {res['filled']}")
        out(f"- خالی: {res['empty']}")
        out(f"- کد ۱۰ رقمی معتبر: {res['valid_10_digit']}")
        out("- نمونه مقادیر:")
        for s in res["samples"][:8]:
            out(f"  - `{s}`")
    else:
        out("ستون کد ملی با نام‌های متداول یافت نشد.")
    out()

    out("## ۷. تحلیل ستون خالص دریافتی")
    out()
    if found["net_received"]:
        col = found["net_received"]
        ser = df[col]
        res = analyze_net_received(ser)
        out(f"- نام ستون: `{col}`")
        out(f"- تعداد کل: {res['total']}")
        out(f"- پر (عددی): {res['filled']}")
        out(f"- خالی/غیرعددی: {res['empty']}")
        out(f"- **جمع خالص دریافتی**: {res['sum']:,.0f}")
        out(f"- کمینه: {res['min']}")
        out(f"- بیشینه: {res['max']}")
        out("- نمونه مقادیر:")
        for v in res["samples"][:8]:
            out(f"  - {v}")
    else:
        out("ستون خالص دریافتی با نام‌های متداول یافت نشد.")
    out()

    out("## ۸. تحلیل ستون نام بیمار")
    out()
    if found["patient_name"]:
        col = found["patient_name"]
        ser = df[col]
        filled = ser.dropna().astype(str).str.strip()
        filled = filled[filled != ""]
        out(f"- نام ستون: `{col}`")
        out(f"- پر: {len(filled)}")
        out("- نمونه:")
        for v in filled.head(5).tolist():
            out(f"  - {v}")
    else:
        out("ستون نام بیمار یافت نشد.")
    out()

    out("## ۹. تحلیل ستون شماره پرونده")
    out()
    if found["record_no"]:
        col = found["record_no"]
        ser = df[col]
        filled = ser.dropna().astype(str).str.strip()
        filled = filled[filled != ""]
        out(f"- نام ستون: `{col}`")
        out(f"- پر: {len(filled)}")
        out(f"- تعداد مقدار یکتا: {filled.nunique()}")
        out("- نمونه:")
        for v in filled.head(5).tolist():
            out(f"  - {v}")
    else:
        out("ستون شماره پرونده یافت نشد.")
    out()

    out("## ۱۰. خلاصه")
    out()
    out("- در این اکسل ستون‌های **تلفن**، **کد ملی** و **خالص دریافتی** شناسایی و تحلیل شدند.")
    out("- از این فایل می‌توان برای تطابق هویت (تلفن، کد ملی) و محاسبات مالی (خالص دریافتی) استفاده کرد.")
    out()

    # ذخیره گزارش در فایل
    report_path = REPO / "docs" / "reports" / "payments_1403_full_excel_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nگزارش ذخیره شد: {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
