"""Inspect unfinished treatments Excel file to see actual structure."""
import sys
import os
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from app.loaders.excel_io import load_workbook, get_sheet_grid
from app.utils.fa_normalize import normalize_fa

filepath = Path("data/inputs/درمانهای نا تمام.xlsx")

print(f"Inspecting: {filepath}")
print("="*80)

wb = load_workbook(str(filepath))

print(f"\nNumber of sheets: {len(wb.worksheets)}")
print("Sheet names:")
for idx, sheet in enumerate(wb.worksheets):
    print(f"  [{idx}] {sheet.title}")

print("\n" + "="*80)
print("SHEET 0 - All rows:")
print("="*80)

sheet = wb.worksheets[0]
grid = get_sheet_grid(sheet, normalize=True)

for row_idx, row in enumerate(grid):
    # Get first few non-empty cells
    cells = [str(cell) if cell else "---" for cell in row[:5]]
    print(f"Row {row_idx:2d}: {' | '.join(cells)}")
    
    # Show normalized version of first cell if it exists
    if row and row[0]:
        normalized = normalize_fa(str(row[0]))
        print(f"         Normalized: '{normalized}'")
        print(f"         Length: {len(normalized)}, Has Persian: {any('\u0600' <= c <= '\u06FF' for c in normalized)}")

print("\n" + "="*80)
print(f"Total rows in sheet: {len(grid)}")
