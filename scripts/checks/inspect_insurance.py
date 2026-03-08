"""Inspect insurance priority Excel file."""
import sys
import os
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from app.loaders.excel_io import load_workbook, get_sheet_grid
from app.utils.fa_normalize import normalize_fa

filepath = Path("data/inputs/تاریخ پرداختی بیمه ها.xlsx")

print(f"Inspecting: {filepath}")
print("="*80)

wb = load_workbook(str(filepath))

print(f"\nNumber of sheets: {len(wb.worksheets)}")

sheet = wb.worksheets[0]
grid = get_sheet_grid(sheet, normalize=True)

print("\nAll rows (first 10 columns):")
print("="*80)

for row_idx, row in enumerate(grid[:25]):
    # Get first 10 cells
    cells = [str(cell)[:20] if cell else "---" for cell in row[:10]]
    print(f"Row {row_idx:2d}: {' | '.join(cells)}")

print("\n" + "="*80)
print(f"Total rows: {len(grid)}")
