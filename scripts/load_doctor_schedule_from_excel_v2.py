from pathlib import Path
import re
import sqlite3
import pandas as pd

DB = r".\atieh_clinic.db"
EXCEL = Path(r"C:\Users\USER\Documents\GitHub\atieh\data\inputs\reference\doctor_schedule.xlsx")
SOURCE_FILE = EXCEL.name

SHEET_INDEXES = [0, 1, 2]

WEEKDAYS = [
    "\u0634\u0646\u0628\u0647",      # شنبه
    "\u06cc\u06a9\u0634\u0646\u0628\u0647",  # یکشنبه
    "\u062f\u0648\u0634\u0646\u0628\u0647",  # دوشنبه
    "\u0633\u0647 \u0634\u0646\u0628\u0647", # سه شنبه
    "\u0686\u0647\u0627\u0631\u0634\u0646\u0628\u0647", # چهارشنبه
    "\u067e\u0646\u062c\u0634\u0646\u0628\u0647", # پنجشنبه
    "\u062c\u0645\u0639\u0647"       # جمعه
]

DOCTOR_WORD = "\u062f\u06a9\u062a\u0631"   # دکتر
AGHAYE_DOCTOR = "\u0622\u0642\u0627\u06cc \u062f\u06a9\u062a\u0631"  # آقای دکتر
SHORT_DOCTOR = "\u062f "  # د 

SHIFT_MORNING = "\u0634\u06cc\u0641\u062a \u0635\u0628\u062d"   # شیفت صبح
SHIFT_AFTERNOON = "\u0634\u06cc\u0641\u062a \u0639\u0635\u0631" # شیفت عصر
SHIFT_NIGHT = "\u0634\u06cc\u0641\u062a \u0634\u0628"           # شیفت شب
UNIT_WORD = "\u06cc\u0648\u0646\u06cc\u062a"                   # یونیت
FLOOR_WORD = "\u0637\u0628\u0642\u0647"                         # طبقه
KOLA_WORD = "\u06a9\u0644\u0627"                               # کلا

def norm_text(x):
    if pd.isna(x):
        return ""
    s = str(x).replace("\u200c", " ").replace("\xa0", " ").replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def clean_doctor_name(text):
    t = norm_text(text)
    if not t:
        return None

    if (DOCTOR_WORD in t) or (AGHAYE_DOCTOR in t) or t.startswith(SHORT_DOCTOR):
        t = t.replace(AGHAYE_DOCTOR, DOCTOR_WORD)
        t = re.sub(r"\(\s*[^)]*\)", "", t)
        t = re.sub(UNIT_WORD + r"\s*\d+", "", t)
        t = re.sub(FLOOR_WORD + r"\s*\S+", "", t)
        t = re.sub(KOLA_WORD + r".*", "", t)
        t = re.sub(r"\d{2,}[-/]\d{2,}", "", t)
        t = re.sub(r"\b\d+\b", "", t)
        t = re.sub(r"\s+", " ", t).strip(" -")
        return t if t else None

    return None

def detect_doctor_columns(df):
    doctor_cols = {}
    for r in [0, 1]:
        for c in range(df.shape[1]):
            cell = norm_text(df.iat[r, c])
            dname = clean_doctor_name(cell)
            if dname:
                doctor_cols[c] = dname
    return doctor_cols

def detect_weekday(block_text):
    for d in WEEKDAYS:
        if d in block_text:
            return d
    return None

def detect_shift(block_text):
    if SHIFT_MORNING in block_text:
        return "morning"
    if SHIFT_AFTERNOON in block_text:
        return "afternoon"
    if SHIFT_NIGHT in block_text:
        return "night"
    return None

def detect_shift_range(block_text):
    m = re.search(r"(\d{1,2})\s*-\s*(\d{1,2})", block_text)
    if not m:
        return None, None
    return f"{int(m.group(1)):02d}:00", f"{int(m.group(2)):02d}:00"

def detect_unit(block_text):
    m = re.search(UNIT_WORD + r"\s*(\d+)", block_text)
    if m:
        return f"{UNIT_WORD} {m.group(1)}"
    return None

def parse_slots(block_text, shift_start=None, shift_end=None):
    slots = []

    # نیم‌ساعتی‌ها: 9/30
    for h, m in re.findall(r"(\d{1,2})\s*/\s*(00|30)", block_text):
        hh = int(h)
        if 6 <= hh <= 23:
            slots.append(f"{hh:02d}:{m}")

    # ساعتی‌ها: 9-10-11-12
    for n in re.findall(r"(?<![/\d])(\d{1,2})(?![/\d])", block_text):
        hh = int(n)
        if 6 <= hh <= 23:
            slots.append(f"{hh:02d}:00")

    # حذف بازه‌ی اصلی شیفت
    to_remove = set()
    if shift_start:
        to_remove.add(shift_start)
    if shift_end:
        to_remove.add(shift_end)

    cleaned = []
    seen = set()
    for s in slots:
        if s in to_remove:
            continue
        if s not in seen:
            seen.add(s)
            cleaned.append(s)

    return cleaned

def upsert_doctor(cur, doctor_name, floor_label):
    cur.execute(
        "INSERT OR IGNORE INTO doctor_master (doctor_name, floor_label) VALUES (?, ?)",
        (doctor_name, floor_label)
    )
    cur.execute(
        "SELECT doctor_id FROM doctor_master WHERE doctor_name = ?",
        (doctor_name,)
    )
    row = cur.fetchone()
    return row[0]

def ensure_tables(cur):
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS doctor_master (
        doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_name TEXT NOT NULL UNIQUE,
        floor_label TEXT,
        active INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS doctor_shift_schedule (
        shift_id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_id INTEGER NOT NULL,
        source_sheet TEXT,
        weekday_name TEXT,
        shift_label TEXT,
        shift_start TEXT,
        shift_end TEXT,
        floor_label TEXT,
        raw_text TEXT,
        source_file TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS doctor_time_slots (
        slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_id INTEGER NOT NULL,
        source_sheet TEXT,
        weekday_name TEXT,
        shift_label TEXT,
        slot_start TEXT NOT NULL,
        floor_label TEXT,
        unit_label TEXT,
        availability_status TEXT NOT NULL DEFAULT 'available',
        raw_text TEXT,
        source_file TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)

def main():
    if not EXCEL.exists():
        raise FileNotFoundError(f"Excel file not found: {EXCEL}")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    ensure_tables(cur)

    cur.execute("DELETE FROM doctor_time_slots")
    cur.execute("DELETE FROM doctor_shift_schedule")
    cur.execute("DELETE FROM doctor_master")
    conn.commit()

    xls = pd.ExcelFile(EXCEL)

    total_doctors = 0
    total_shifts = 0
    total_slots = 0

    for idx in SHEET_INDEXES:
        sheet_name = xls.sheet_names[idx]
        df = pd.read_excel(EXCEL, sheet_name=sheet_name, header=None)

        doctor_cols = detect_doctor_columns(df)
        print(f"SHEET {idx} | {sheet_name} | detected_doctor_cols={len(doctor_cols)}")

        for col, doctor_name in sorted(doctor_cols.items()):
            doctor_id = upsert_doctor(cur, doctor_name, sheet_name)
            total_doctors += 1

            for r in range(2, len(df)):
                left = max(0, col - 2)
                right = col
                block_cells = [norm_text(df.iat[r, c]) for c in range(left, right + 1)]
                block_cells = [x for x in block_cells if x]
                if not block_cells:
                    continue

                block_text = " | ".join(block_cells)

                weekday = detect_weekday(block_text)
                shift_label = detect_shift(block_text)
                shift_start, shift_end = detect_shift_range(block_text)

                if not weekday or not shift_label:
                    continue

                unit_label = detect_unit(block_text)
                slots = parse_slots(block_text, shift_start, shift_end)

                cur.execute("""
                    INSERT INTO doctor_shift_schedule (
                        doctor_id, source_sheet, weekday_name, shift_label,
                        shift_start, shift_end, floor_label, raw_text, source_file
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doctor_id, sheet_name, weekday, shift_label,
                    shift_start, shift_end, sheet_name, block_text, SOURCE_FILE
                ))
                total_shifts += 1

                for slot in slots:
                    cur.execute("""
                        INSERT INTO doctor_time_slots (
                            doctor_id, source_sheet, weekday_name, shift_label,
                            slot_start, floor_label, unit_label, availability_status,
                            raw_text, source_file
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'available', ?, ?)
                    """, (
                        doctor_id, sheet_name, weekday, shift_label,
                        slot, sheet_name, unit_label, block_text, SOURCE_FILE
                    ))
                    total_slots += 1

    conn.commit()
    conn.close()

    print(f"IMPORT DONE | doctors={total_doctors} shifts={total_shifts} slots={total_slots}")

if __name__ == "__main__":
    main()
