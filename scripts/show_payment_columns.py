import pandas as pd

df = pd.read_excel(r"data/inputs/payments/payments_1403_full.xlsx")

print("COLUMNS:")
for c in df.columns:
    print(repr(c))
