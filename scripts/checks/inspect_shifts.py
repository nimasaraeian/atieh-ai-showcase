"""Inspect the structure of the doctor shifts Excel file."""
import sys
import os
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from app.loaders.excel_io import load_workbook, get_sheet_grid

filepath = Path("data/inputs/reference/__نوبت دهی 17 دی_.xlsx")

print(f"Inspecting: {filepath}")
print("="*80)

wb = load_workbook(str(filepath))

print(f"\nNumber of sheets: {len(wb.worksheets)}")
print("Sheet names:")
for idx, sheet in enumerate(wb.worksheets):
    print(f"  [{idx}] {sheet.title}")

for sheet_idx in [0, 3]:  # Check sheet 0 and sheet 3 (دندانپزشکان شیفت)
    print("\n" + "="*80)
    print(f"SHEET {sheet_idx} - {wb.worksheets[sheet_idx].title} - First 20 rows:")
    print("="*80)

    sheet = wb.worksheets[sheet_idx]
    grid = get_sheet_grid(sheet, normalize=True)

    for row_idx, row in enumerate(grid[:20]):
        # Print first 8 columns
        cells = [str(cell)[:25] if cell else "---" for cell in row[:8]]
        print(f"Row {row_idx:2d}: {' | '.join(cells)}")

    print(f"\nTotal rows in sheet: {len(grid)}")
    print(f"Total cols in first row: {len(grid[0]) if grid else 0}")
