# settings_manager.py
import json
import os
import config
import logging
from datetime import datetime, timedelta # <-- Ensure timedelta is imported if used elsewhere

logger = logging.getLogger(__name__)

class SettingsManager:
    def __init__(self, filename=config.SETTINGS_FILENAME):
        self.filepath = filename
        self.settings = self._load_settings()

    def _load_settings(self):
        defaults = {
            "shift_start": config.DEFAULT_SHIFT_START,
            "shift_end": config.DEFAULT_SHIFT_END,
            "swipe_delay_minutes": config.DEFAULT_SWIPE_DELAY_MINUTES,
            "database_folder": config.DEFAULT_DATA_FOLDER,
            "log_folder": os.path.join(config.DEFAULT_DATA_FOLDER, config.DEFAULT_LOG_FOLDER_NAME),
            "backup_folder": config.DEFAULT_BACKUP_FOLDER,
            "allowed_swipe_window_minutes": config.DEFAULT_ALLOWED_SWIPE_WINDOW_MINUTES,
            # --- Add VID/PID Defaults ---
            "zkteco_vid": config.DEFAULT_ZKTeco_VID,
            "zkteco_pid": config.DEFAULT_ZKTeco_PID,
        }
        if not os.path.exists(self.filepath):
            logger.warning(f"Settings file '{self.filepath}' not found. Creating with defaults.")
            self.settings = defaults
            self.save_settings() # Save defaults immediately
            return defaults
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
            # Ensure all keys exist, add defaults if missing
            settings_updated = False
            for key, value in defaults.items():
                if key not in loaded_settings:
                    logger.warning(f"Setting '{key}' missing. Adding default value: {value}")
                    loaded_settings[key] = value
                    settings_updated = True # Mark that we added defaults

            # Save back if defaults were added to an existing file
            if settings_updated:
                 self.settings = loaded_settings # Update internal settings first
                 self.save_settings() # Save the file with added defaults

            return loaded_settings
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading settings from '{self.filepath}': {e}. Using default settings.")
            # Optionally backup corrupted file here
            self.settings = defaults # Use defaults in memory
            # Don't save over corrupted file automatically, maybe warn user
            return defaults


    def get_setting(self, key, default=None):
        # Provide a fallback default if the key is somehow still missing
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value
        logger.info(f"Setting '{key}' updated to '{value}'")

    def save_settings(self):
        try:
            os.makedirs(os.path.dirname(self.filepath) or '.', exist_ok=True)
            with open(self.filepath, 'w', encoding='utf-8') as f:
                # Ensure VID/PID are saved as integers (JSON standard)
                settings_to_save = self.settings.copy()
                if "zkteco_vid" in settings_to_save:
                    settings_to_save["zkteco_vid"] = int(settings_to_save["zkteco_vid"])
                if "zkteco_pid" in settings_to_save:
                     settings_to_save["zkteco_pid"] = int(settings_to_save["zkteco_pid"])

                json.dump(settings_to_save, f, indent=4, ensure_ascii=False)
            logger.info(f"Settings saved to '{self.filepath}'")
        except IOError as e:
            logger.error(f"Error saving settings to '{self.filepath}': {e}")
        except Exception as e:
             logger.error(f"Unexpected error saving settings: {e}")

    def get_shift_times(self):
        try:
            start_time = datetime.strptime(self.get_setting("shift_start"), "%H:%M").time()
            end_time = datetime.strptime(self.get_setting("shift_end"), "%H:%M").time()
            return start_time, end_time
        except (ValueError, TypeError):
            logger.error("Invalid shift time format in settings. Using defaults.")
            start_time = datetime.strptime(config.DEFAULT_SHIFT_START, "%H:%M").time()
            end_time = datetime.strptime(config.DEFAULT_SHIFT_END, "%H:%M").time()
            return start_time, end_time

    def get_swipe_delay(self):
        return timedelta(minutes=self.get_setting("swipe_delay_minutes", config.DEFAULT_SWIPE_DELAY_MINUTES))

    def get_allowed_swipe_window(self):
        return timedelta(minutes=self.get_setting("allowed_swipe_window_minutes", config.DEFAULT_ALLOWED_SWIPE_WINDOW_MINUTES))