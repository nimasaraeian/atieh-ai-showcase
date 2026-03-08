import pandas as pd
from pathlib import Path

files = sorted(Path(".").rglob("payments_*.xlsx"))
print("FILES FOUND:")
for f in files:
    print("-", f)

if files:
    df = pd.read_excel(files[0], nrows=3)
    print("\nFIRST FILE:", files[0].name)
    print("\nCOLUMNS:")
    for c in df.columns:
        print(repr(str(c)))
else:
    print("NO FILES FOUND")
