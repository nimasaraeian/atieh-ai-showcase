from datetime import time

SHIFT_WINDOWS = {
    "D": (time(8, 0), time(14, 0)),
    "E": (time(14, 0), time(20, 0)),
    "N": (time(20, 0), time(0, 0)),
}


def shift_window(shift_code: str):
    return SHIFT_WINDOWS[shift_code]

