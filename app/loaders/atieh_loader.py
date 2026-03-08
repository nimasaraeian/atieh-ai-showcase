"""Main data loader for Atieh scheduling engine."""
import pandas as pd
import logging
from pathlib import Path
from typing import List, Dict, Any
import re

from app.loaders.excel_io import (
    load_workbook, get_sheet_grid, find_sheet_by_keyword, 
    get_first_sheet, is_row_empty
)
from app.utils.fa_normalize import normalize_fa, extract_tags, split_doctors

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# File paths – Excel inputs live in data/inputs/reference/
DATA_DIR = Path("data")
INPUT_DIR = DATA_DIR / "inputs"
OUTPUT_DIR = DATA_DIR / "outputs"
REFERENCE_DIR = DATA_DIR / "inputs" / "reference"

# Excel filenames (no hardcoded paths; build via REFERENCE_DIR)
_EXCEL_FILES = {
    "shifts": "__نوبت دهی 17 دی_.xlsx",
    "services": "خدمات اقای سرایی.xlsx",
    "unfinished": "درمانهای نا تمام.xlsx",
    "insurance": "تاریخ پرداختی بیمه ها.xlsx",
}
SHIFTS_FILE = REFERENCE_DIR / _EXCEL_FILES["shifts"]
SERVICES_FILE = REFERENCE_DIR / _EXCEL_FILES["services"]
UNFINISHED_FILE = REFERENCE_DIR / _EXCEL_FILES["unfinished"]
INSURANCE_FILE = REFERENCE_DIR / _EXCEL_FILES["insurance"]


def _ensure_excel_exists(filepath: Path) -> None:
    """If file does not exist, log WARNING and raise FileNotFoundError."""
    if not filepath.exists():
        logger.warning("Excel file not found: %s", filepath)
        raise FileNotFoundError(f"Excel file not found: {filepath}")


def parse_doctor_shifts(filepath: Path = SHIFTS_FILE) -> pd.DataFrame:
    """
    Parse doctor shift schedule from Excel file.
    
    Expected structure:
    - Uses sheet named "دندانپزشکان شیفت" (Dentists Shift)
    - Columns: weekday, morning doctors, evening doctors, night doctors
    - Persian weekdays: شنبه, یکشنبه, دوشنبه, سه شنبه, چهارشنبه, پنجشنبه, جمعه
    - Multiple doctors separated by -, --, newline, or multiple spaces
    - Tags in parentheses like (اطفال)
    
    Returns:
        DataFrame with columns:
        - weekday_fa: Persian weekday
        - shift_code: D (day/morning), E (evening), N (night)
        - doctor_name_raw: Original doctor name
        - doctor_name_norm: Normalized doctor name
        - tags: Extracted tags (comma-separated)
    """
    _ensure_excel_exists(filepath)
    logger.info(f"Parsing doctor shifts from {filepath}")
    wb = load_workbook(str(filepath))
    
    # Look for the sheet with shift schedule
    # Prefer "دندانپزشکان شیفت" or similar
    sheet = find_sheet_by_keyword(wb, ['دندانپزشکان', 'شیفت', 'shift'])
    if not sheet:
        # Fallback to first sheet
        sheet = get_first_sheet(wb)
    
    grid = get_sheet_grid(sheet, normalize=True)
    
    # Find rows containing weekday names
    persian_weekdays = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه']
    
    records = []
    
    for row_idx, row in enumerate(grid):
        if not row or len(row) < 4:
            continue
        
        # Check if first column contains a weekday
        first_cell = str(row[0]) if row[0] else ""
        weekday = None
        
        for wd in persian_weekdays:
            if wd in first_cell:
                weekday = wd
                break
        
        if not weekday:
            continue
        
        # Columns: [weekday, morning/D, evening/E, night/N]
        shifts = [
            ('D', row[1] if len(row) > 1 else None),  # Morning/Day
            ('E', row[2] if len(row) > 2 else None),  # Evening
            ('N', row[3] if len(row) > 3 else None),  # Night
        ]
        
        for shift_code, cell_value in shifts:
            if not cell_value:
                continue
            
            # Skip if it's just "---" or similar placeholder
            cell_str = str(cell_value).strip()
            if not cell_str or cell_str == '---' or cell_str == 'None':
                continue
            
            # Split multiple doctors
            doctor_list = split_doctors(cell_str)
            
            for doctor_raw in doctor_list:
                if not doctor_raw or len(doctor_raw) < 2:
                    continue
                
                # Extract tags
                doctor_clean, tags = extract_tags(doctor_raw)
                
                if doctor_clean and len(doctor_clean) >= 2:
                    # Apply doctor name normalization (removes "دکتر" prefix, etc.)
                    from app.utils.name_normalize import normalize_doctor_name
                    doctor_normalized = normalize_doctor_name(doctor_clean)
                    
                    records.append({
                        'weekday_fa': weekday,
                        'shift_code': shift_code,
                        'doctor_name_raw': doctor_raw,
                        'doctor_name_norm': doctor_normalized if doctor_normalized else doctor_clean,
                        'tags': ','.join(tags) if tags else ''
                    })
    
    df = pd.DataFrame(records)
    logger.info(f"Parsed {len(df)} doctor shift entries")
    return df


def parse_services_catalog(filepath: Path = SERVICES_FILE) -> pd.DataFrame:
    """
    Parse services catalog from Excel file.
    
    Expected structure:
    - Category headers like: "نوع خدمات(جراحی)"
    - Service rows following each category
    
    Returns:
        DataFrame with columns:
        - category: Service category
        - service_name: Original service name
        - service_name_norm: Normalized service name
        - default_duration_min: Estimated duration in minutes
        - complexity_weight: Complexity score (0.0-1.0)
    """
    _ensure_excel_exists(filepath)
    logger.info(f"Parsing services catalog from {filepath}")
    wb = load_workbook(str(filepath))
    sheet = get_first_sheet(wb)
    grid = get_sheet_grid(sheet, normalize=True)
    
    records = []
    current_category = "عمومی"  # Default category
    
    # Keywords that indicate category headers
    category_keywords = ['نوع', 'خدمات', 'دسته', 'بخش']
    
    for row in grid:
        if not row or is_row_empty(row):
            continue
        
        # Get first non-empty cell
        first_cell = next((cell for cell in row if cell), None)
        if not first_cell:
            continue
        
        first_cell_str = str(first_cell)
        
        # Check if this is a category header
        is_category = False
        for keyword in category_keywords:
            if keyword in first_cell_str:
                is_category = True
                # Extract category name (text in parentheses or after keyword)
                match = re.search(r'\(([^)]+)\)', first_cell_str)
                if match:
                    current_category = match.group(1)
                else:
                    current_category = first_cell_str
                break
        
        if is_category:
            logger.debug(f"Found category: {current_category}")
            continue
        
        # This is a service row
        service_name = first_cell_str.strip()
        if not service_name or len(service_name) < 2:
            continue
        
        # Heuristic for duration and complexity based on service name
        duration, complexity = estimate_service_params(service_name)
        
        records.append({
            'category': current_category,
            'service_name': service_name,
            'service_name_norm': normalize_fa(service_name),
            'default_duration_min': duration,
            'complexity_weight': complexity
        })
    
    df = pd.DataFrame(records)
    logger.info(f"Parsed {len(df)} services")
    return df


def estimate_service_params(service_name: str) -> tuple:
    """
    Estimate duration and complexity for a service based on its name.
    
    Returns:
        (duration_minutes, complexity_weight)
    """
    service_lower = service_name.lower()
    
    # High complexity, long duration
    if any(kw in service_lower for kw in ['ایمپلنت', 'کاشت', 'جراحی', 'surgery']):
        return (90, 1.0)
    
    # Medium-high complexity
    if any(kw in service_lower for kw in ['ریشه', 'root', 'عصب', 'درمان مجدد']):
        return (60, 0.9)
    
    if any(kw in service_lower for kw in ['روکش', 'پروتز', 'بریج', 'crown']):
        return (45, 0.7)
    
    # Medium complexity
    if any(kw in service_lower for kw in ['کشیدن', 'extraction', 'کامپوزیت', 'ترمیم', 'filling']):
        return (30, 0.6)
    
    # Low complexity
    if any(kw in service_lower for kw in ['جرمگیری', 'scaling', 'بروساژ', 'polish']):
        return (30, 0.4)
    
    # Default
    return (30, 0.5)


def parse_unfinished_catalog(filepath: Path = UNFINISHED_FILE) -> pd.DataFrame:
    """
    Parse unfinished treatments catalog.
    
    The Excel file structure has:
    - Column 0: Row numbers (1, 2, 3, ...)
    - Column 1: Treatment titles (actual data we want)
    
    Returns:
        DataFrame with columns:
        - backlog_title: Treatment title
        - urgency_weight: Urgency score (0.0-1.0)
    """
    _ensure_excel_exists(filepath)
    logger.info(f"Parsing unfinished treatments from {filepath}")
    wb = load_workbook(str(filepath))
    sheet = get_first_sheet(wb)
    grid = get_sheet_grid(sheet, normalize=True)
    
    records = []
    raw_titles = []
    
    # Keywords to identify and skip header/metadata rows
    skip_keywords = ['عنوان', 'نوع', 'title', 'type', 'درمانها', 'درمان ها', 
                     'ناتمام', 'نا تمام', 'ردیف', 'row', 'number']
    
    # The structure is:
    # - Row 0: Merged header "درمانهای ناتمام"
    # - Row 1: Sub-headers: "ردیف" (column 0), "درمانهای ناتمام" (column 1)
    # - Row 2+: Row number (column 0), Treatment title (column 1)
    treatment_col_idx = 1  # Treatment titles are in column 1
    header_rows = 2  # Skip first 2 rows (main header + sub-header)
    
    logger.info(f"Using column {treatment_col_idx} for treatment titles, skipping first {header_rows} rows")
    
    for row_idx, row in enumerate(grid):
        if row_idx < header_rows:  # Skip header rows
            continue
            
        if not row or len(row) <= treatment_col_idx:
            continue
        
        # Get treatment title from the detected column
        title = row[treatment_col_idx]
        if not title:
            continue
        
        title = str(title)
        
        # Store raw for logging
        raw_titles.append(title)
        
        # Normalize
        title_norm = normalize_fa(title.strip())
        title_lower = title_norm.lower()
        
        # Skip if too short
        if len(title_norm) < 3:
            logger.debug(f"Row {row_idx}: Skipped (too short): '{title_norm}'")
            continue
        
        # Skip if it's purely numeric or contains only digits and spaces
        if title_norm.replace(' ', '').replace('-', '').isdigit():
            logger.debug(f"Row {row_idx}: Skipped (numeric): '{title_norm}'")
            continue
        
        # Skip header-like rows
        if any(kw in title_lower for kw in skip_keywords):
            logger.debug(f"Row {row_idx}: Skipped (header): '{title_norm}'")
            continue
        
        # Check if it has at least some Persian characters
        persian_chars = sum(1 for c in title_norm if '\u0600' <= c <= '\u06FF')
        if persian_chars < 2:
            logger.debug(f"Row {row_idx}: Skipped (no Persian): '{title_norm}'")
            continue
        
        # Passed all filters - add to records
        urgency = estimate_urgency(title_norm)
        
        logger.debug(f"Row {row_idx}: Kept: '{title_norm}' (urgency: {urgency:.2f})")
        
        records.append({
            'backlog_title': title_norm,
            'urgency_weight': urgency
        })
    
    # Deduplicate
    df = pd.DataFrame(records)
    if not df.empty:
        df = df.drop_duplicates(subset=['backlog_title'], keep='first')
    
    logger.info(f"Parsed unfinished treatments:")
    logger.info(f"  Raw rows examined: {len(raw_titles)}")
    logger.info(f"  Rows kept after filtering: {len(df)}")
    
    if len(df) > 0:
        logger.info(f"  First {min(10, len(df))} treatment titles:")
        for idx, title in enumerate(df['backlog_title'].head(10), 1):
            logger.info(f"    {idx}. {title} (urgency: {df.iloc[idx-1]['urgency_weight']:.2f})")
    else:
        logger.warning("  No valid treatment titles found!")
    
    return df


def estimate_urgency(treatment_title: str) -> float:
    """
    Estimate urgency weight for an unfinished treatment.
    
    Returns:
        Urgency score between 0.0 and 1.0
    """
    title_lower = treatment_title.lower()
    
    # Highest urgency
    if any(kw in title_lower for kw in ['ایمپلنت', 'جراحی', 'surgery', 'implant']):
        return 1.0
    
    if any(kw in title_lower for kw in ['ریشه', 'root', 'عصب', 'درمان مجدد']):
        return 0.9
    
    if any(kw in title_lower for kw in ['روکش', 'پروتز', 'تحویل', 'crown', 'delivery']):
        return 0.7
    
    if any(kw in title_lower for kw in ['ارتودنسی', 'ortho']):
        return 0.5
    
    # Default
    return 0.6


def parse_insurance_priority(filepath: Path = INSURANCE_FILE) -> pd.DataFrame:
    """
    Parse insurance payment priority data.
    
    Expected structure:
    - Row 0: Merged header "اولویت بندی بیمه ها"
    - Row 1: Column headers: ردیف, نام بیمه, یک ماه, دو ماه, ...
    - Row 2+: Row number (col 0), Insurance name (col 1), '*' markers (cols 2-6)
    
    Returns:
        DataFrame with columns:
        - insurance_name: Insurance company name
        - priority_score: Priority score (1.0 = highest, 0.2 = lowest)
    """
    _ensure_excel_exists(filepath)
    logger.info(f"Parsing insurance priorities from {filepath}")
    
    wb = load_workbook(str(filepath))
    sheet = get_first_sheet(wb)
    grid = get_sheet_grid(sheet, normalize=True)
    
    # Map bucket names to priority scores
    bucket_priority = {
        'یک ماه': 1.0,
        'one_month': 1.0,
        '1': 1.0,
        'دو ماه': 0.8,
        'two_month': 0.8,
        '2': 0.8,
        'سه ماه': 0.6,
        'three_month': 0.6,
        '3': 0.6,
        'چهار ماه': 0.4,
        'four_month': 0.4,
        '4': 0.4,
        'پنج ماه': 0.2,
        'five_month': 0.2,
        'بیشتر': 0.2,  # بیشتر از 5 ماه
        'over_five': 0.2,
        '5': 0.2,
    }
    
    records = []
    
    # The structure is clear:
    # Row 0: Main header (merged)
    # Row 1: Column headers
    # Row 2+: Data
    header_row = 1
    insurance_col_idx = 1  # Insurance names are in column 1
    
    headers = grid[header_row] if header_row < len(grid) else []
    logger.info(f"Using column {insurance_col_idx} for insurance names, header row {header_row}")
    logger.debug(f"Headers: {headers[:7]}")
    
    # Process data rows (starting from row 2)
    for row_idx, row in enumerate(grid):
        if row_idx <= header_row:  # Skip header rows
            continue
            
        if not row or len(row) <= insurance_col_idx:
            continue
        
        # Get insurance name from column 1
        insurance_name = row[insurance_col_idx]
        if not insurance_name:
            continue
        
        insurance_name = str(insurance_name).strip()
        
        # Skip if it's too short or looks like a number
        if len(insurance_name) < 2 or insurance_name.isdigit():
            logger.debug(f"Row {row_idx}: Skipped '{insurance_name}' (too short or numeric)")
            continue
        
        # Skip header-like rows
        if any(kw in insurance_name.lower() for kw in ['بیمه', 'نام', 'name', 'insurance', 'ردیف']):
            logger.debug(f"Row {row_idx}: Skipped '{insurance_name}' (header keyword)")
            continue
        
        # Look for '*' marker in row to determine priority
        priority_score = 0.5  # Default
        
        for col_idx in range(2, min(len(row), len(headers))):  # Start from column 2 (bucket columns)
            cell = row[col_idx]
            if cell and '*' in str(cell):
                # Match column header to priority bucket
                if col_idx < len(headers):
                    header = normalize_fa(str(headers[col_idx]).lower())
                    for bucket_key, score in bucket_priority.items():
                        if bucket_key in header:
                            priority_score = score
                            logger.debug(f"Row {row_idx}: '{insurance_name}' -> bucket '{headers[col_idx]}' -> score {score}")
                            break
                break
        
        records.append({
            'insurance_name': normalize_fa(insurance_name),
            'priority_score': priority_score
        })
    
    df = pd.DataFrame(records)
    logger.info(f"Parsed {len(df)} insurance entries")
    
    if len(df) > 0:
        logger.info(f"  First {min(10, len(df))} insurance entries:")
        for idx, row in df.head(10).iterrows():
            logger.info(f"    {idx+1}. {row['insurance_name']} -> priority: {row['priority_score']:.2f}")
    
    return df


def save_csv(df: pd.DataFrame, filename: str):
    """Save DataFrame to CSV in output directory."""
    output_path = OUTPUT_DIR / filename
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    logger.info(f"Saved {len(df)} rows to {output_path}")


def main():
    """Main entry point - load all data and generate CSVs."""
    logger.info("Starting Atieh data loader...")
    
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # Parse and save doctor shifts
        logger.info("\n" + "="*60)
        logger.info("LOADING DOCTOR SHIFTS")
        logger.info("="*60)
        df_shifts = parse_doctor_shifts()
        save_csv(df_shifts, "doctor_shifts.csv")
        
        # Parse and save services catalog
        logger.info("\n" + "="*60)
        logger.info("LOADING SERVICES CATALOG")
        logger.info("="*60)
        df_services = parse_services_catalog()
        save_csv(df_services, "services_catalog.csv")
        
        # Parse and save unfinished treatments
        logger.info("\n" + "="*60)
        logger.info("LOADING UNFINISHED TREATMENTS")
        logger.info("="*60)
        df_unfinished = parse_unfinished_catalog()
        save_csv(df_unfinished, "unfinished_treatments.csv")
        
        # Parse and save insurance priorities
        logger.info("\n" + "="*60)
        logger.info("LOADING INSURANCE PRIORITIES")
        logger.info("="*60)
        df_insurance = parse_insurance_priority()
        save_csv(df_insurance, "insurance_priority.csv")
        
        logger.info("\n" + "="*60)
        logger.info("SUCCESS! All data loaded and saved to data/outputs/")
        logger.info("="*60)
        logger.info(f"Doctor shifts: {len(df_shifts)} entries")
        logger.info(f"Services: {len(df_services)} entries")
        logger.info(f"Unfinished treatments: {len(df_unfinished)} entries")
        logger.info(f"Insurance priorities: {len(df_insurance)} entries")
        
    except FileNotFoundError as e:
        logger.error(f"\nERROR: Input file not found: {e}")
        logger.error("Please ensure all Excel files are in data/inputs/ directory")
        return 1
    except Exception as e:
        logger.error(f"\nERROR: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
