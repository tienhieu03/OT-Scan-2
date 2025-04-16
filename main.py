# main.py
import sys
import os
import logging
import queue
from datetime import datetime
from tkinter import messagebox

import config
from settings_manager import SettingsManager
from employee_manager import EmployeeManager
from ot_log_manager import OTLogManager
from attendance_manager import AttendanceManager
from hid_handler import HidHandler
from simulator_hid_handler import SimulatorHidHandler
from ui_manager import UIManager

USE_SIMULATOR = False # Set to False to use real HID handler

# --- Logging Setup ---
log_format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
log_level = logging.INFO # Change to logging.DEBUG for more details
# Create a logs directory if it doesn't exist
log_dir = "app_logs"
os.makedirs(log_dir, exist_ok=True)
log_filename = os.path.join(log_dir, f"ot_manager_{datetime.now().strftime('%Y%m%d')}.log")

# Basic console logging
logging.basicConfig(level=log_level, format=log_format)

# File logging
file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setFormatter(logging.Formatter(log_format))
logging.getLogger().addHandler(file_handler) # Add handler to root logger

logger = logging.getLogger(__name__)

# --- Main Application Class ---
class Application:
    def __init__(self):
        logger.info("Initializing OT Manager Application...")
        self.hid_queue = queue.Queue()

        # Initialize Managers
        self.settings_manager = SettingsManager() # Load settings first
        logger.info("Settings Manager initialized.")
        self.employee_manager = EmployeeManager(self.settings_manager)
        logger.info("Employee Manager initialized.")
        self.ot_log_manager = OTLogManager(self.settings_manager)
        logger.info("OT Log Manager initialized.")

        # Initialize UI Manager
        self.ui_manager = UIManager(
            attendance_manager=None,
            settings_manager=self.settings_manager,
            employee_manager=self.employee_manager,
            ot_log_manager=self.ot_log_manager,
            hid_queue=self.hid_queue
        )
        logger.info("UI Manager initialized.")

        # Initialize Attendance Manager
        self.attendance_manager = AttendanceManager(
            settings_manager=self.settings_manager,
            employee_manager=self.employee_manager,
            ot_log_manager=self.ot_log_manager,
            ui_update_callback=self.ui_manager.update_display
        )
        self.ui_manager.attendance_manager = self.attendance_manager
        logger.info("Attendance Manager initialized.")

        # Conditional Handler Initialization
        self.hid_handler = None
        if USE_SIMULATOR:
            self.hid_handler = SimulatorHidHandler(self.hid_queue)
            logger.info(">>> Using HID Simulator <<<")
            self.ui_manager.after(100, lambda: self.ui_manager.update_hid_status("SIMULATOR MODE ACTIVE"))
        else:
            logger.info(">>> Using Real HID Handler <<<")
            if sys.platform == "win32":
                try:
                    # --- Get VID/PID from settings ---
                    # Use defaults from config as fallback
                    vid = self.settings_manager.get_setting("zkteco_vid", config.DEFAULT_ZKTeco_VID)
                    pid = self.settings_manager.get_setting("zkteco_pid", config.DEFAULT_ZKTeco_PID)
                    logger.info(f"Attempting to use VID=0x{vid:04X}, PID=0x{pid:04X} from settings.")

                    # --- Pass VID/PID to HidHandler ---
                    self.hid_handler = HidHandler(self.hid_queue, vid, pid)

                    # logger.info("HID Handler (pywinusb) initialized.") # Already logged in HidHandler init
                    self.ui_manager.update_hid_status("Tìm kiếm thiết bị...")
                except Exception as e:
                    logger.error(f"Failed to initialize real HidHandler: {e}", exc_info=True) # Log traceback
                    messagebox.showerror("Lỗi HID", f"Không thể khởi tạo bộ đọc thẻ thật:\n{e}\n\nKiểm tra driver, VID/PID trong cài đặt, hoặc thử chế độ Simulator.")
                    self.ui_manager.update_hid_status("Lỗi khởi tạo HID")
            else:
                logger.error("Real HID handling currently only supported on Windows with pywinusb.")
                messagebox.showwarning("Không tương thích", "Đọc thẻ HID thật chỉ hỗ trợ trên Windows.\nChuyển sang chế độ Simulator nếu muốn tiếp tục.")
                self.ui_manager.update_hid_status("Không hỗ trợ trên OS này")

        self._perform_backups()
        self.ui_manager.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        logger.info("Close request received. Shutting down...")
        # Now messagebox is defined because of the import at the top
        if messagebox.askokcancel("Thoát", "Bạn có chắc chắn muốn thoát OT Manager?"):
            # ... (rest of the shutdown code) ...
            logger.info("Destroying UI...")
            self.ui_manager.destroy()
            logger.info("Application shutdown complete.")
            sys.exit() # Ensure process terminates fully
        else:
             logger.info("Shutdown cancelled by user.")

    def _perform_backups(self):
        logger.info("Performing startup backups...")
        try:
            self.employee_manager.backup_database()
        except Exception as e:
            logger.error(f"Error during database backup: {e}")
        try:
            self.ot_log_manager.backup_current_log()
        except Exception as e:
            logger.error(f"Error during log backup: {e}")
        logger.info("Startup backups completed.")


    def run(self):
        logger.info("Starting application...")
        if self.hid_handler:
            self.hid_handler.start()
            # Give HID handler a moment to find devices initially
            # Update status based on initial find result? (Needs callback from HID)
            # For now, assume it's searching. Status updates can come from logs/handler.
            self.ui_manager.update_hid_status("Đang chạy...") # Or update based on find result
        else:
             self.ui_manager.update_hid_status("Lỗi - Không thể đọc thẻ")

        self.ui_manager.run() # Starts the Tkinter main loop


# --- Entry Point ---
if __name__ == "__main__":
    # Create essential folders if they don't exist
    try:
        os.makedirs(config.DEFAULT_DATA_FOLDER, exist_ok=True)
        # Use settings manager to get potentially customized log/backup folders for creation check
        temp_settings = SettingsManager() # Load settings to get paths
        log_folder = config.get_log_folder(temp_settings) # Gets path and creates if needed
        db_backup_folder = config.get_backup_folder(temp_settings, type="db") # Gets path and creates if needed
        log_backup_folder = config.get_backup_folder(temp_settings, type="log") # Gets path and creates if needed
        del temp_settings # No longer needed
    except Exception as e:
        logger.error(f"Error creating initial directories: {e}")
        # Optionally show an error to the user here if folder creation fails

    app = Application()
    app.run()