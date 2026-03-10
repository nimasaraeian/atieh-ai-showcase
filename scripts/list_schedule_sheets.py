from pathlib import Path
import pandas as pd

EXCEL = Path(r'C:\Users\USER\Documents\GitHub\atieh\data\inputs\reference\doctor_schedule.xlsx')

xls = pd.ExcelFile(EXCEL)

for i, name in enumerate(xls.sheet_names):
    print(f'{i}: {name}')
