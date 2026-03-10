from pathlib import Path
import re
import pandas as pd

EXCEL = Path(r'C:\Users\USER\Documents\GitHub\atieh\data\inputs\reference\doctor_schedule.xlsx')
FLOOR_SHEETS = ['????1', '???? 2', '???? ??? ? ?????']

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

    if '????' in t or '???? ????' in t or t.startswith('? '):
        t = t.replace('???? ????', '????')
        t = re.sub(r'\(\s*[^)]*\)', '', t)
        t = re.sub(r'?????\s*\d+', '', t)
        t = re.sub(r'????\s*\S+', '', t)
        t = re.sub(r'???.*', '', t)
        t = re.sub(r'\d{2,}[-/]\d{2,}', '', t)
        t = re.sub(r'\b\d+\b', '', t)
        t = re.sub(r'\s+', ' ', t).strip(' -')
        return t if t else None

    return None

def main():
    if not EXCEL.exists():
        raise FileNotFoundError(f'Excel file not found: {EXCEL}')

    xls = pd.ExcelFile(EXCEL)

    for sheet in FLOOR_SHEETS:
        if sheet not in xls.sheet_names:
            continue

        print('=' * 100)
        print(f'SHEET: {sheet}')
        df = pd.read_excel(EXCEL, sheet_name=sheet, header=None)
        max_cols = df.shape[1]

        found = []

        for c in range(max_cols):
            for r in range(min(20, len(df))):
                cell = norm_text(df.iat[r, c])
                if not cell:
                    continue
                dname = clean_doctor_name(cell)
                if dname:
                    found.append((c, r, dname, cell))

        if not found:
            print('NO DOCTORS DETECTED')
        else:
            for item in found[:100]:
                c, r, dname, raw = item
                print(f'col={c} row={r} -> doctor={dname} | raw={raw}')

if __name__ == '__main__':
    main()
