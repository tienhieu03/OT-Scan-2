# config.py
import os
import sys
from datetime import datetime

# --- File Paths ---
DEFAULT_DATA_FOLDER = "data"
DEFAULT_LOG_FOLDER_NAME = "logs"
DEFAULT_BACKUP_FOLDER = "backup"
DB_FILENAME = "employee_database.xlsx"
SETTINGS_FILENAME = "settings.json"
LOG_FILENAME_PREFIX = "OT_Log_Thang_"
LOG_FILENAME_DATE_FORMAT = "%m_%Y" # MM_YYYY
BACKUP_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

# --- Excel Structure ---
DB_COLUMNS = ["STT", "Họ tên", "ID", "CARD ID"]
LOG_BASE_COLUMNS = ["STT", "Họ tên", "ID"]
LOG_ROW_TYPES = ["Giờ Vào", "Giờ Ra", "Tổng thời gian"] # 3 rows per employee

def get_base_path():
    """ Get the base path for data files, whether running as script or frozen exe """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # If the application is run as a PyInstaller bundle (--onefile)
        # sys.executable points to the executable itself
        return os.path.dirname(sys.executable)
    elif getattr(sys, 'frozen', False):
         # If the application is run as a PyInstaller bundle (--onedir)
         # sys.executable points to the executable itself
         return os.path.dirname(sys.executable)
    else:
        # If run as a normal script (__file__ points to config.py)
        # Go one level up if config.py is not in the root? Assuming it is.
        # If main.py and config.py are in the same root folder, this works.
        return os.path.dirname(os.path.abspath(__file__))

# --- Call the function ONCE to define the base path ---
BASE_PATH = get_base_path()

# --- File Paths (Update these to use BASE_PATH) ---
DEFAULT_DATA_FOLDER = os.path.join(BASE_PATH, "data")
DEFAULT_LOG_FOLDER_NAME = "logs" # Keep as relative name for joining later
DEFAULT_BACKUP_FOLDER = os.path.join(BASE_PATH, "backup")
# Settings file should be relative to the exe/script
SETTINGS_FILENAME = os.path.join(BASE_PATH, "settings.json")
DB_FILENAME = "employee_database.xlsx" # Keep as relative name
LOG_FILENAME_PREFIX = "OT_Log_Thang_"
LOG_FILENAME_DATE_FORMAT = "%m_%Y" # MM_YYYY
BACKUP_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

# --- Excel Structure ---
DB_COLUMNS = ["STT", "Họ tên", "ID", "CARD ID"]
LOG_BASE_COLUMNS = ["STT", "Họ tên", "ID"]
LOG_ROW_TYPES = ["Giờ Vào", "Giờ Ra", "Tổng thời gian"]

# --- Default Settings ---
DEFAULT_SHIFT_START = "08:00"
DEFAULT_SHIFT_END = "17:15"
DEFAULT_SWIPE_DELAY_MINUTES = 1
DEFAULT_ALLOWED_SWIPE_WINDOW_MINUTES = 15
DEFAULT_ZKTeco_VID = 0x1b55 # Example VID - VERIFY!
DEFAULT_ZKTeco_PID = 0xb502 # Example PID - VERIFY!

# --- OT Rules ---
MONTHLY_OT_LIMIT_HOURS = 83.0
MONTHLY_OT_LIMIT_MINUTES = MONTHLY_OT_LIMIT_HOURS * 60

# --- Other ---
APP_TITLE = "OT Manager - Quản lý chấm công"
MAX_LOG_DISPLAY_ENTRIES = 50

# --- Dynamic Paths ---
def get_db_filepath(settings_mgr):
    folder = settings_mgr.get_setting("database_folder", DEFAULT_DATA_FOLDER)
    return os.path.join(folder, DB_FILENAME)

def get_log_folder(settings_mgr):
    folder = settings_mgr.get_setting("log_folder", os.path.join(DEFAULT_DATA_FOLDER, DEFAULT_LOG_FOLDER_NAME))
    os.makedirs(folder, exist_ok=True)
    return folder

def get_log_filepath(settings_mgr, target_date=None):
    if target_date is None:
        target_date = datetime.now()
    log_folder = get_log_folder(settings_mgr)
    filename = f"{LOG_FILENAME_PREFIX}{target_date.strftime(LOG_FILENAME_DATE_FORMAT)}.xlsx"
    return os.path.join(log_folder, filename)

def get_backup_folder(settings_mgr, type="db"): # type can be 'db' or 'log'
    base_backup_folder = settings_mgr.get_setting("backup_folder", DEFAULT_BACKUP_FOLDER)
    subfolder = "db_backups" if type == "db" else "log_backups"
    folder = os.path.join(base_backup_folder, subfolder)
    os.makedirs(folder, exist_ok=True)
    return folder