import logging
import re
from typing import Iterable

import pandas as pd

from app.loaders.excel_io import (
    forward_fill_merged_cells,
    load_workbook_safe,
    normalize_cell,
    sheet_to_grid,
)
from app.utils.fa_normalize import normalize_fa, normalize_tokens

logger = logging.getLogger(__name__)

WEEKDAYS_FA = [
    "شنبه",
    "یکشنبه",
    "دوشنبه",
    "سه شنبه",
    "سه‌شنبه",
    "چهارشنبه",
    "پنجشنبه",
    "جمعه",
]

SHIFT_META = {
    "D": ("morning", "08:00", "14:00"),
    "E": ("afternoon", "14:00", "20:00"),
    "N": ("night", "20:00", "24:00"),
}

SPLIT_PATTERN = re.compile(r"\s*-\s*|\n")
PARENS_PATTERN = re.compile(r"\(([^)]+)\)")


def _first_non_empty(items: Iterable[str | None]) -> str | None:
    for item in items:
        if item is None:
            continue
        value = normalize_cell(item)
        if value:
            return value
    return None


def _split_doctors(value: str) -> list[str]:
    if not value:
        return []
    normalized = normalize_fa(value)
    parts = SPLIT_PATTERN.split(normalized)
    return normalize_tokens(parts)


def _extract_tags(name: str) -> tuple[str, list[str]]:
    tags = []
    for match in PARENS_PATTERN.findall(name):
        if match:
            tags.append(normalize_fa(match))
    cleaned = PARENS_PATTERN.sub("", name).strip()
    return cleaned, tags


def parse_doctor_shifts(path: str) -> pd.DataFrame:
    wb = load_workbook_safe(path)
    ws = wb["دندانپزشکان شیفت"]
    grid = forward_fill_merged_cells(ws, sheet_to_grid(ws))

    rows = []
    for row in grid:
        weekday_cell = _first_non_empty(row)
        if weekday_cell is None:
            continue
        weekday_norm = normalize_fa(weekday_cell)
        if weekday_norm not in WEEKDAYS_FA:
            continue
        weekday_index = next(
            (idx for idx, cell in enumerate(row) if normalize_cell(cell) == weekday_cell),
            0,
        )
        shift_cells = row[weekday_index + 1 : weekday_index + 4]
        if len(shift_cells) < 3:
            continue
        for shift_code, cell_value in zip(["D", "E", "N"], shift_cells):
            if cell_value is None:
                continue
            raw_text = normalize_cell(cell_value)
            if not raw_text:
                continue
            for doctor_raw in _split_doctors(raw_text):
                doctor_name, tags = _extract_tags(doctor_raw)
                doctor_norm = normalize_fa(doctor_name)
                tag_list = list(tags)
                if doctor_norm == "گردشی":
                    tag_list.append("گردشی")
                shift_label, start_time, end_time = SHIFT_META[shift_code]
                rows.append(
                    {
                        "weekday_fa": weekday_norm,
                        "shift_code": shift_code,
                        "shift_label": shift_label,
                        "start_time": start_time,
                        "end_time": end_time,
                        "doctor_name_raw": doctor_raw,
                        "doctor_name_norm": doctor_norm,
                        "tags": "|".join(tag_list) if tag_list else "",
                    }
                )

    df = pd.DataFrame(rows)
    logger.info("Parsed doctor shifts: %s rows", len(df))
    return df


def parse_insurance_priority(path: str) -> pd.DataFrame:
    wb = load_workbook_safe(path)
    ws = wb["Sheet1"]
    grid = forward_fill_merged_cells(ws, sheet_to_grid(ws))

    bucket_map = {
        "one_month": 1.0,
        "two_month": 0.8,
        "three_month": 0.6,
        "four_month": 0.4,
        "over_five_month": 0.2,
    }
    header_row = None
    bucket_cols = {}
    for row_idx, row in enumerate(grid):
        normalized_row = [normalize_cell(cell) for cell in row]
        for col_idx, cell in enumerate(normalized_row):
            if not cell:
                continue
            if "یک" in cell and "ماه" in cell:
                bucket_cols["one_month"] = col_idx
            if "دو" in cell and "ماه" in cell:
                bucket_cols["two_month"] = col_idx
            if "سه" in cell and "ماه" in cell:
                bucket_cols["three_month"] = col_idx
            if "چهار" in cell and "ماه" in cell:
                bucket_cols["four_month"] = col_idx
            if "پنج" in cell or "بیش" in cell:
                if "ماه" in cell:
                    bucket_cols["over_five_month"] = col_idx
        if len(bucket_cols) >= 3:
            header_row = row_idx
            break

    rows = []
    start_idx = (header_row + 1) if header_row is not None else 0
    for row in grid[start_idx:]:
        insurance_name = _first_non_empty(row)
        if not insurance_name:
            continue
        bucket = None
        for bucket_name, col_idx in bucket_cols.items():
            if col_idx >= len(row):
                continue
            marker = normalize_cell(row[col_idx])
            if marker and ("*" in marker or marker in {"✓", "x", "X"}):
                bucket = bucket_name
                break
        if bucket is None:
            continue
        rows.append(
            {
                "insurance_name": normalize_fa(insurance_name),
                "bucket": bucket,
                "priority_score": bucket_map[bucket],
            }
        )

    df = pd.DataFrame(rows)
    logger.info("Parsed insurance priorities: %s rows", len(df))
    return df


def _service_defaults(service_name: str) -> tuple[int, float]:
    value = normalize_fa(service_name)
    if "ایمپلنت" in value or "جراحی" in value:
        return 90, 1.0
    if "کشیدن" in value:
        return 30, 0.6
    if "ترمیم" in value or "کامپوزیت" in value:
        return 45, 0.5
    if "جرمگیری" in value:
        return 30, 0.4
    return 30, 0.5


def parse_services_catalog(path: str) -> pd.DataFrame:
    wb = load_workbook_safe(path)
    ws = wb["Sheet1"]
    grid = forward_fill_merged_cells(ws, sheet_to_grid(ws))

    rows = []
    current_category = None
    for row in grid:
        cell = _first_non_empty(row)
        if not cell:
            continue
        value = normalize_fa(cell)
        if value.startswith("نوع خدمات") and "(" in value and ")" in value:
            current_category = value
            continue
        if current_category is None:
            continue
        duration, complexity = _service_defaults(value)
        rows.append(
            {
                "category": current_category,
                "service_name": value,
                "service_name_norm": normalize_fa(value),
                "default_duration_min": duration,
                "complexity_weight": complexity,
            }
        )

    df = pd.DataFrame(rows)
    logger.info("Parsed services catalog: %s rows", len(df))
    return df


def _urgency_weight(title: str) -> float:
    value = normalize_fa(title)
    if "درمان ریشه" in value or "درمان مجدد ریشه" in value:
        return 0.9
    if "ایمپلنت" in value or "جراحی سینوس" in value or "پیوند" in value:
        return 1.0
    if "ارتودنسی" in value:
        return 0.5
    if "تحویل پروتز" in value or "روکش" in value:
        return 0.7
    if "قدامی" in value:
        return 0.8
    return 0.6


def parse_unfinished_catalog(path: str) -> pd.DataFrame:
    wb = load_workbook_safe(path)
    ws = wb["Sheet1"]
    grid = forward_fill_merged_cells(ws, sheet_to_grid(ws))

    header_idx = None
    for idx, row in enumerate(grid):
        row_text = " ".join(normalize_tokens([normalize_cell(cell) for cell in row if cell]))
        if "درمان" in row_text and "ناتمام" in row_text:
            header_idx = idx
            break

    rows = []
    for row in grid[(header_idx + 1) if header_idx is not None else 0 :]:
        normalized_row = [normalize_cell(cell) for cell in row]
        normalized_row = [cell for cell in normalized_row if cell]
        if not normalized_row:
            continue
        backlog_code = None
        backlog_title = None
        for cell in normalized_row:
            if cell.isdigit():
                backlog_code = int(cell)
            else:
                backlog_title = cell
                break
        if backlog_title is None and normalized_row:
            backlog_title = normalized_row[0]
        if not backlog_title:
            continue
        rows.append(
            {
                "backlog_code": backlog_code if backlog_code is not None else len(rows) + 1,
                "backlog_title": normalize_fa(backlog_title),
                "urgency_weight": _urgency_weight(backlog_title),
            }
        )

    df = pd.DataFrame(rows)
    logger.info("Parsed unfinished treatments: %s rows", len(df))
    return df
