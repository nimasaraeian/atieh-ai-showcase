from pathlib import Path
import pandas as pd
import re

EXCEL = Path(r'C:\Users\USER\Documents\GitHub\atieh\data\inputs\reference\doctor_schedule.xlsx')
sheet = '????1'

def norm_text(x):
    if pd.isna(x):
        return ''
    s = str(x).replace('\u200c', ' ').replace('\xa0', ' ').replace('\n', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    return s

df = pd.read_excel(EXCEL, sheet_name=sheet, header=None)

for r in range(0, 12):
    vals = []
    for c in range(df.shape[1]):
        cell = norm_text(df.iat[r, c])
        if cell:
            vals.append(f'[{r},{c}] {cell}')
    if vals:
        print('=' * 80)
        for v in vals:
            print(v)
