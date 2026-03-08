"""Time block and slot generation for scheduling."""
from typing import List, Tuple
from datetime import time, timedelta


# Shift definitions
SHIFT_BLOCKS = {
    'D': (time(8, 0), time(14, 0)),   # Day/Morning: 08:00-14:00
    'E': (time(14, 0), time(20, 0)),  # Evening: 14:00-20:00
    'N': (time(20, 0), time(23, 59)),  # Night: 20:00-23:59 (end of day)
}

# For calculations, treat N shift as ending at minute 1440 (24:00 equivalent)
SHIFT_BLOCKS_MINUTES = {
    'D': (480, 840),   # 08:00-14:00
    'E': (840, 1200),  # 14:00-20:00
    'N': (1200, 1440), # 20:00-24:00 (using 1440 minutes = 24:00)
}

# Persian weekdays in order
WEEKDAYS = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه']


def time_to_minutes(t: time) -> int:
    """Convert time object to minutes since midnight."""
    return t.hour * 60 + t.minute


def minutes_to_time(minutes: int) -> time:
    """Convert minutes since midnight to time object."""
    hours = minutes // 60
    mins = minutes % 60
    # Handle 24:00 case
    if hours >= 24:
        hours = 23
        mins = 59
    return time(hours, mins)


def generate_slots(shift_code: str, slot_minutes: int = 30) -> List[Tuple[str, str]]:
    """
    Generate time slots for a given shift.
    
    Args:
        shift_code: Shift code (D/E/N)
        slot_minutes: Duration of each slot in minutes
        
    Returns:
        List of (start_time, end_time) tuples as strings (HH:MM format)
    """
    if shift_code not in SHIFT_BLOCKS_MINUTES:
        raise ValueError(f"Invalid shift code: {shift_code}")
    
    start_min, end_min = SHIFT_BLOCKS_MINUTES[shift_code]
    
    slots = []
    current_min = start_min
    
    while current_min + slot_minutes <= end_min:
        slot_start = minutes_to_time(current_min)
        slot_end = minutes_to_time(current_min + slot_minutes)
        
        slots.append((
            slot_start.strftime('%H:%M'),
            slot_end.strftime('%H:%M')
        ))
        
        current_min += slot_minutes
    
    return slots


def generate_all_slots(slot_minutes: int = 30) -> List[dict]:
    """
    Generate all possible slots for all weekdays and shifts.
    
    Args:
        slot_minutes: Duration of each slot in minutes
        
    Returns:
        List of slot dictionaries with weekday, shift_code, start_time, end_time
    """
    all_slots = []
    
    for weekday in WEEKDAYS:
        for shift_code in ['D', 'E', 'N']:
            slots = generate_slots(shift_code, slot_minutes)
            for start_time, end_time in slots:
                all_slots.append({
                    'weekday': weekday,
                    'shift_code': shift_code,
                    'start_time': start_time,
                    'end_time': end_time
                })
    
    return all_slots


def is_night_shift(shift_code: str) -> bool:
    """Check if a shift is night shift."""
    return shift_code == 'N'


def get_shift_name(shift_code: str) -> str:
    """Get Persian name for shift code."""
    names = {
        'D': 'صبح',
        'E': 'عصر',
        'N': 'شب'
    }
    return names.get(shift_code, shift_code)
