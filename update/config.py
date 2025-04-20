# config.py
import os
import sys
from datetime import datetime

# ... (get_base_path function and BASE_PATH definition) ...

# --- File Paths ---
# ... (remain the same) ...
SETTINGS_FILENAME = os.path.join(BASE_PATH, "settings.json")
# ...

# --- Default Settings ---
# REMOVE old single shift defaults:
# DEFAULT_SHIFT_START = "08:00"
# DEFAULT_SHIFT_END = "17:00"

DEFAULT_SWIPE_DELAY_MINUTES = 1
DEFAULT_ALLOWED_SWIPE_WINDOW_MINUTES = 15
DEFAULT_ZKTeco_VID = 0xFFFF # Example VID - VERIFY!
DEFAULT_ZKTeco_PID = 0x0035 # Example PID - VERIFY!

# --- ADD Default Multi-Shift Structure ---
DEFAULT_SHIFTS = [
    {"name": "Hành chính", "start": "08:00", "end": "17:00"},
    {"name": "Ca 1",        "start": "06:00", "end": "14:00"},
    {"name": "Ca 2",        "start": "14:00", "end": "22:00"},
    {"name": "Ca 3",        "start": "22:00", "end": "06:00"} # Overnight example
]
DEFAULT_ACTIVE_SHIFT_NAME = "Hành chính" # Default active shift
# --- END ADD ---


# --- OT Rules ---
# ... (remain the same) ...

# --- Other ---
# ... (remain the same) ...

# --- Dynamic Paths ---
# ... (remain the same) ...