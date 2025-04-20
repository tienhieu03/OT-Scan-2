# settings_manager.py
import json
import os
import config
import logging
from datetime import datetime, time, timedelta # Ensure time is imported

logger = logging.getLogger(__name__)

class SettingsManager:
    def __init__(self, filename=config.SETTINGS_FILENAME):
        self.filepath = filename
        self.settings = self._load_settings()

    def _load_settings(self):
        defaults = {
            # REMOVE old single shift defaults if they were here
            "swipe_delay_minutes": config.DEFAULT_SWIPE_DELAY_MINUTES,
            "database_folder": config.DEFAULT_DATA_FOLDER,
            "log_folder": os.path.join(config.DEFAULT_DATA_FOLDER, config.DEFAULT_LOG_FOLDER_NAME),
            "backup_folder": config.DEFAULT_BACKUP_FOLDER,
            "allowed_swipe_window_minutes": config.DEFAULT_ALLOWED_SWIPE_WINDOW_MINUTES,
            "zkteco_vid": config.DEFAULT_ZKTeco_VID,
            "zkteco_pid": config.DEFAULT_ZKTeco_PID,
            # --- ADD New Defaults ---
            "shifts": config.DEFAULT_SHIFTS,
            "active_shift_name": config.DEFAULT_ACTIVE_SHIFT_NAME,
            # --- END ADD ---
        }
        # ... (rest of loading logic remains the same - it will add missing keys) ...
        # Ensure the loading logic correctly adds 'shifts' and 'active_shift_name' if missing
        if not os.path.exists(self.filepath):
            logger.warning(f"Settings file '{self.filepath}' not found. Creating with defaults.")
            self.settings = defaults
            self.save_settings() # Save defaults immediately
            return defaults
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)

            settings_updated = False
            for key, value in defaults.items():
                # Special check for 'shifts' structure if needed (e.g., ensure list of dicts)
                if key == "shifts" and key in loaded_settings:
                     if not isinstance(loaded_settings[key], list) or not all(isinstance(item, dict) for item in loaded_settings[key]):
                          logger.warning(f"Setting '{key}' has incorrect format. Overwriting with default.")
                          loaded_settings[key] = value
                          settings_updated = True
                elif key not in loaded_settings:
                    logger.warning(f"Setting '{key}' missing. Adding default value: {value}")
                    loaded_settings[key] = value
                    settings_updated = True

            if settings_updated:
                 self.settings = loaded_settings
                 self.save_settings()

            # Ensure active_shift_name actually exists in the loaded shifts
            loaded_shifts = loaded_settings.get("shifts", [])
            loaded_active_name = loaded_settings.get("active_shift_name", config.DEFAULT_ACTIVE_SHIFT_NAME)
            shift_names = [s.get("name") for s in loaded_shifts if s.get("name")]
            if loaded_active_name not in shift_names:
                 logger.warning(f"Active shift '{loaded_active_name}' not found in shifts list. Resetting to default '{config.DEFAULT_ACTIVE_SHIFT_NAME}'.")
                 loaded_settings["active_shift_name"] = config.DEFAULT_ACTIVE_SHIFT_NAME
                 self.settings = loaded_settings # Update internal state
                 self.save_settings() # Save the correction

            return loaded_settings
        except (json.JSONDecodeError, IOError, TypeError) as e: # Added TypeError
            logger.error(f"Error loading settings from '{self.filepath}': {e}. Using default settings.", exc_info=True)
            self.settings = defaults
            return defaults


    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value
        logger.info(f"Setting '{key}' updated to '{value}'")

    def save_settings(self):
        # ... (saving logic for VID/PID remains the same) ...
        try:
            os.makedirs(os.path.dirname(self.filepath) or '.', exist_ok=True)
            with open(self.filepath, 'w', encoding='utf-8') as f:
                settings_to_save = self.settings.copy()
                if "zkteco_vid" in settings_to_save:
                    settings_to_save["zkteco_vid"] = int(settings_to_save["zkteco_vid"])
                if "zkteco_pid" in settings_to_save:
                     settings_to_save["zkteco_pid"] = int(settings_to_save["zkteco_pid"])
                # Ensure shifts list is saved correctly (should be fine by default)
                json.dump(settings_to_save, f, indent=4, ensure_ascii=False)
            logger.info(f"Settings saved to '{self.filepath}'")
        except Exception as e:
             logger.error(f"Unexpected error saving settings: {e}", exc_info=True)


    # --- RENAME and MODIFY get_shift_times ---
    def get_active_shift_times(self):
        """Gets the start and end time for the currently active shift."""
        active_name = self.get_setting("active_shift_name", config.DEFAULT_ACTIVE_SHIFT_NAME)
        all_shifts = self.get_setting("shifts", config.DEFAULT_SHIFTS)

        active_shift_info = None
        for shift in all_shifts:
            if isinstance(shift, dict) and shift.get("name") == active_name:
                active_shift_info = shift
                break

        if not active_shift_info:
            logger.error(f"Active shift '{active_name}' not found in settings. Using first shift as fallback.")
            # Fallback to the first shift in the list or the absolute default
            if all_shifts and isinstance(all_shifts[0], dict):
                 active_shift_info = all_shifts[0]
            else: # Absolute fallback if settings are completely broken
                 active_shift_info = config.DEFAULT_SHIFTS[0]

        try:
            start_str = active_shift_info.get("start", "00:00")
            end_str = active_shift_info.get("end", "00:00")
            start_time = datetime.strptime(start_str, "%H:%M").time()
            end_time = datetime.strptime(end_str, "%H:%M").time()
            logger.debug(f"Using active shift '{active_shift_info.get('name')}': {start_str} - {end_str}")
            return start_time, end_time
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid time format for shift '{active_shift_info.get('name')}': {e}. Using 00:00-00:00.")
            return time(0, 0), time(0, 0) # Return default time objects on error

    # --- ADD Helper Methods ---
    def get_all_shifts(self):
        """Returns the list of all configured shift dictionaries."""
        return self.get_setting("shifts", config.DEFAULT_SHIFTS)

    def get_shift_names(self):
        """Returns a list of names of all configured shifts."""
        all_shifts = self.get_all_shifts()
        return [s.get("name", "Unnamed Shift") for s in all_shifts if isinstance(s, dict)]
    # --- END ADD ---


    def get_swipe_delay(self):
        delay_minutes = self.get_setting("swipe_delay_minutes", config.DEFAULT_SWIPE_DELAY_MINUTES)
        try:
             # Ensure it's at least 0
             return timedelta(minutes=max(0, int(delay_minutes)))
        except (ValueError, TypeError):
             logger.warning(f"Invalid swipe_delay_minutes '{delay_minutes}'. Using default.")
             return timedelta(minutes=config.DEFAULT_SWIPE_DELAY_MINUTES)


    def get_allowed_swipe_window(self):
         window_minutes = self.get_setting("allowed_swipe_window_minutes", config.DEFAULT_ALLOWED_SWIPE_WINDOW_MINUTES)
         try:
              return timedelta(minutes=max(0, int(window_minutes)))
         except (ValueError, TypeError):
              logger.warning(f"Invalid allowed_swipe_window_minutes '{window_minutes}'. Using default.")
              return timedelta(minutes=config.DEFAULT_ALLOWED_SWIPE_WINDOW_MINUTES)