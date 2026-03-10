from pathlib import Path
import pandas as pd
import re

EXCEL = Path(r'C:\Users\USER\Documents\GitHub\atieh\data\inputs\reference\doctor_schedule.xlsx')
SHEET_INDEX = 1   # ????? ??? ?????? 0 ?? 2 ?? ??? ???????

def norm_text(x):
    if pd.isna(x):
        return ''
    s = str(x).replace('\u200c', ' ').replace('\xa0', ' ').replace('\n', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    return s

xls = pd.ExcelFile(EXCEL)
sheet_name = xls.sheet_names[SHEET_INDEX]
print(f'SHEET_INDEX={SHEET_INDEX}')
print(f'SHEET_NAME={sheet_name}')
print('=' * 90)

df = pd.read_excel(EXCEL, sheet_name=sheet_name, header=None)

for r in range(0, 12):
    vals = []
    for c in range(df.shape[1]):
        cell = norm_text(df.iat[r, c])
        if cell:
            vals.append(f'[{r},{c}] {cell}')
    if vals:
        print('=' * 90)
        for v in vals:
            print(v)
