from datetime import datetime, timedelta, time

from app.engine.time_blocks import SHIFT_WINDOWS


def _to_minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def _format_time(minutes: int) -> str:
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def build_slots(weekday: str, shift_code: str, slot_minutes: int = 30) -> list[dict]:
    start_time, end_time = SHIFT_WINDOWS[shift_code]
    start_minutes = _to_minutes(start_time)
    end_minutes = _to_minutes(end_time)
    if end_minutes == 0:
        end_minutes = 24 * 60

    slots = []
    current = start_minutes
    while current + slot_minutes <= end_minutes:
        slots.append(
            {
                "weekday": weekday,
                "shift_code": shift_code,
                "slot_start": _format_time(current),
                "slot_end": _format_time(current + slot_minutes),
            }
        )
        current += slot_minutes
    return slots
