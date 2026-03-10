from pathlib import Path
import re
import sqlite3
import pandas as pd

DB = r'.\atieh_clinic.db'
EXCEL = Path(r'C:\Users\USER\Documents\GitHub\atieh\data\inputs\reference\doctor_schedule.xlsx')
SOURCE_FILE = EXCEL.name

FLOOR_SHEETS = ['????1', '???? 2', '???? ??? ? ?????']
WEEKDAYS = ['????', '??????', '??????', '?? ????', '????????', '???????', '????']

def norm_text(x):
    if pd.isna(x):
        return ''
    s = str(x).replace('\u200c', ' ').replace('\xa0', ' ').replace('\n', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def clean_doctor_name(text):
    t = norm_text(text)
    if not t:
        return None
    if '????' in t or '? ' in t or t.startswith('???? ????'):
        t = t.replace('???? ????', '????')
        t = re.sub(r'\(\s*[^)]*\)', '', t)
        t = re.sub(r'?????\s*\d+', '', t)
        t = re.sub(r'???.*', '', t)
        t = re.sub(r'\d{2,}[-/]\d{2,}', '', t)
        t = re.sub(r'\b\d+\b', '', t)
        t = re.sub(r'\s+', ' ', t).strip(' -')
        return t.strip() if t else None
    return None

def parse_weekday_and_shift(text):
    t = norm_text(text)
    weekday = next((d for d in WEEKDAYS if d in t), None)
    shift_label = None
    shift_start = None
    shift_end = None

    if '???? ???' in t:
        shift_label = 'morning'
    elif '???? ???' in t:
        shift_label = 'afternoon'
    elif '???? ??' in t:
        shift_label = 'night'

    m = re.search(r'(\d{1,2})\s*-\s*(\d{1,2})', t)
    if m:
        shift_start = f"{int(m.group(1)):02d}:00"
        shift_end = f"{int(m.group(2)):02d}:00"

    return weekday, shift_label, shift_start, shift_end

def parse_unit(text):
    t = norm_text(text)
    m = re.search(r'?????\s*(\d+)', t)
    if m:
        return f"????? {m.group(1)}"
    return None

def parse_slots(text):
    t = norm_text(text)
    slots = []

    for h, m in re.findall(r'(\d{1,2})\s*/\s*(00|30)', t):
        slots.append(f"{int(h):02d}:{m}")

    nums = re.findall(r'(?<![/\d])(\d{1,2})(?![/\d])', t)
    for n in nums:
        hour = int(n)
        if 6 <= hour <= 23:
            slots.append(f"{hour:02d}:00")

    if '???? ??? 8-14' in t or '???? ??? 14-20' in t or '???? ?? 20-24' in t:
        shift_nums = set()
        m = re.search(r'(\d{1,2})\s*-\s*(\d{1,2})', t)
        if m:
            shift_nums.add(f"{int(m.group(1)):02d}:00")
            shift_nums.add(f"{int(m.group(2)):02d}:00")
        slots = [s for s in slots if s not in shift_nums]

    seen = set()
    out = []
    for s in slots:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out

def upsert_doctor(cur, doctor_name, floor_label):
    cur.execute(
        "INSERT OR IGNORE INTO doctor_master (doctor_name, floor_label) VALUES (?, ?)",
        (doctor_name, floor_label)
    )
    cur.execute(
        "SELECT doctor_id FROM doctor_master WHERE doctor_name = ?",
        (doctor_name,)
    )
    return cur.fetchone()[0]

def main():
    if not EXCEL.exists():
        raise FileNotFoundError(f'Excel file not found: {EXCEL}')

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("DELETE FROM doctor_time_slots")
    cur.execute("DELETE FROM doctor_shift_schedule")
    cur.execute("DELETE FROM doctor_master")
    conn.commit()

    xls = pd.ExcelFile(EXCEL)

    for sheet in FLOOR_SHEETS:
        if sheet not in xls.sheet_names:
            continue

        df = pd.read_excel(EXCEL, sheet_name=sheet, header=None)
        max_cols = df.shape[1]

        doctor_by_col = {}

        for c in range(max_cols):
            for r in range(min(12, len(df))):
                cell = norm_text(df.iat[r, c])
                dname = clean_doctor_name(cell)
                if dname:
                    doctor_by_col[c] = dname
                    upsert_doctor(cur, dname, sheet)
                    break

        current_weekday = None
        current_shift = None
        current_shift_start = None
        current_shift_end = None

        for r in range(len(df)):
            row_texts = [norm_text(v) for v in df.iloc[r].tolist()]
            joined_row = ' | '.join([x for x in row_texts if x])

            weekday, shift_label, shift_start, shift_end = parse_weekday_and_shift(joined_row)
            if weekday:
                current_weekday = weekday
            if shift_label:
                current_shift = shift_label
                current_shift_start = shift_start
                current_shift_end = shift_end

            if current_weekday and current_shift:
                for c in range(max_cols):
                    doctor_name = doctor_by_col.get(c)
                    if not doctor_name:
                        continue

                    cell_text = norm_text(df.iat[r, c])
                    if not cell_text:
                        continue

                    doctor_id = upsert_doctor(cur, doctor_name, sheet)

                    cur.execute("""
                        INSERT INTO doctor_shift_schedule (
                            doctor_id, source_sheet, weekday_name, shift_label,
                            shift_start, shift_end, floor_label, raw_text, source_file
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        doctor_id, sheet, current_weekday, current_shift,
                        current_shift_start, current_shift_end, sheet, cell_text, SOURCE_FILE
                    ))

                    slots = parse_slots(cell_text)
                    unit_label = parse_unit(cell_text)

                    for slot in slots:
                        cur.execute("""
                            INSERT INTO doctor_time_slots (
                                doctor_id, source_sheet, weekday_name, shift_label,
                                slot_start, floor_label, unit_label, availability_status,
                                raw_text, source_file
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'available', ?, ?)
                        """, (
                            doctor_id, sheet, current_weekday, current_shift,
                            slot, sheet, unit_label, cell_text, SOURCE_FILE
                        ))

        conn.commit()

    conn.close()
    print('Doctor schedule import completed.')

if __name__ == '__main__':
    main()
