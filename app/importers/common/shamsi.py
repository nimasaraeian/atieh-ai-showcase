"""
Jalali (Shamsi) to Gregorian date/time conversion utilities.
"""
import jdatetime
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
from app.importers.common.normalize import normalize_digits


def parse_shamsi_date(date_str: Optional[str]) -> Optional[jdatetime.date]:
    """
    Parse Shamsi date string to jdatetime.date object.
    
    Supports formats:
    - YYYY/MM/DD
    - YYYY-MM-DD
    - YYYY.MM.DD
    - With Persian/Arabic digits
    """
    if not date_str:
        return None
    
    # Normalize digits first
    date_str = normalize_digits(str(date_str).strip())
    
    # Try different separators
    separators = ['/', '-', '.', ' ']
    
    for sep in separators:
        if sep in date_str:
            parts = date_str.split(sep)
            if len(parts) == 3:
                try:
                    year = int(parts[0])
                    month = int(parts[1])
                    day = int(parts[2])
                    
                    # Validate ranges
                    if 1300 <= year <= 1500 and 1 <= month <= 12 and 1 <= day <= 31:
                        return jdatetime.date(year, month, day)
                except (ValueError, TypeError):
                    continue
    
    return None


def parse_time(time_str: Optional[str]) -> Optional[Tuple[int, int]]:
    """
    Parse time string to (hour, minute) tuple.
    
    Supports formats:
    - HH:MM
    - HH.MM
    - With Persian/Arabic digits
    """
    if not time_str:
        return None
    
    # Normalize digits
    time_str = normalize_digits(str(time_str).strip())
    
    # Try different separators
    separators = [':', '.']
    
    for sep in separators:
        if sep in time_str:
            parts = time_str.split(sep)
            if len(parts) >= 2:
                try:
                    hour = int(parts[0])
                    minute = int(parts[1])
                    
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        return (hour, minute)
                except (ValueError, TypeError):
                    continue
    
    # Try parsing as HHMM (no separator)
    if len(time_str) == 4 and time_str.isdigit():
        try:
            hour = int(time_str[:2])
            minute = int(time_str[2:])
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return (hour, minute)
        except (ValueError, TypeError):
            pass
    
    return None


def shamsi_to_gregorian_datetime(
    date_str: Optional[str], 
    time_str: Optional[str] = None
) -> Optional[datetime]:
    """
    Convert Shamsi date (and optional time) to Gregorian datetime.
    
    Args:
        date_str: Shamsi date string (e.g., "1404/01/15")
        time_str: Optional time string (e.g., "14:30")
    
    Returns:
        Gregorian datetime object or None if parsing fails
    """
    shamsi_date = parse_shamsi_date(date_str)
    if not shamsi_date:
        return None
    
    # Convert to Gregorian date
    try:
        gregorian_date = shamsi_date.togregorian()
    except Exception:
        return None
    
    # Add time if provided
    if time_str:
        time_parts = parse_time(time_str)
        if time_parts:
            hour, minute = time_parts
            return datetime.combine(
                gregorian_date,
                datetime.min.time().replace(hour=hour, minute=minute)
            )
    
    # Return datetime at midnight if no time provided
    return datetime.combine(gregorian_date, datetime.min.time())


def build_end_datetime(
    start_dt: datetime, 
    duration_minutes: Optional[int] = None
) -> datetime:
    """
    Calculate end datetime based on start and duration.
    
    Args:
        start_dt: Start datetime
        duration_minutes: Duration in minutes (default: 30)
    
    Returns:
        End datetime
    """
    if duration_minutes is None or duration_minutes <= 0:
        duration_minutes = 30  # Default duration
    
    return start_dt + timedelta(minutes=duration_minutes)


def parse_shamsi_datetime_flexible(text: Optional[str]) -> Optional[datetime]:
    """
    Try to parse date and time from a single text field.
    Handles formats like: "1404/01/15 14:30" or "1404/01/15 ساعت 14:30"
    """
    if not text:
        return None
    
    text = normalize_digits(str(text).strip())
    
    # Try to extract date and time patterns
    # Pattern: YYYY/MM/DD HH:MM or YYYY-MM-DD HH:MM
    pattern = r'(\d{4}[\/-]\d{1,2}[\/-]\d{1,2})\s+(\d{1,2}:\d{2})'
    match = re.search(pattern, text)
    
    if match:
        date_part = match.group(1)
        time_part = match.group(2)
        return shamsi_to_gregorian_datetime(date_part, time_part)
    
    # Try just date
    pattern_date = r'(\d{4}[\/-]\d{1,2}[\/-]\d{1,2})'
    match = re.search(pattern_date, text)
    if match:
        return shamsi_to_gregorian_datetime(match.group(1))
    
    return None
