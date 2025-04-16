# ot_log_manager.py
import pandas as pd
import os
import shutil
from datetime import datetime, timedelta
import calendar # <-- Add this import if missing
import config
import logging

logger = logging.getLogger(__name__)

class OTLogManager:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.current_log_filepath = None # Initialize
        self.df_log = None
        # Determine and load the initial log file path correctly for the current date
        initial_log_path = self._get_log_filepath(datetime.now()) # Calculate path first
        self._load_log_file(initial_log_path) # Load using the specific path

    def _get_log_filepath(self, target_date):
         """Gets the expected log filepath for a given date using settings."""
         return config.get_log_filepath(self.settings_manager, target_date)

    # Renamed _load_log_for_date to _load_log_file for clarity
    def _load_log_file(self, filepath):
        """Loads the specified log file into self.df_log."""
        # No path recalculation here - uses the provided filepath argument

        if filepath == self.current_log_filepath and self.df_log is not None:
            logger.debug(f"Log file already loaded: {filepath}")
            return self.df_log # Already loaded

        logger.info(f"Attempting to load OT log file: {filepath}")
        self.current_log_filepath = filepath # Set the current path being managed

        # --- Determine target_date from filepath for creating/checking columns ---
        target_date = None
        try:
            filename_part = os.path.basename(filepath).replace(config.LOG_FILENAME_PREFIX, '').split('.')[0]
            target_date = datetime.strptime(filename_part, config.LOG_FILENAME_DATE_FORMAT)
        except ValueError:
             logger.error(f"Could not parse date from log filename '{filepath}'. Cannot create/verify structure accurately.")
             # Set df_log to None or empty to indicate failure?
             self.df_log = None
             return None # Indicate failure to load

        try:
            if not os.path.exists(filepath):
                logger.warning(f"Log file '{filepath}' not found. Creating new log sheet.")
                self.df_log = self._create_new_log_sheet(target_date)
                self.save_log() # Save the newly created structure
            else:
                logger.info(f"Loading existing log file: {filepath}")
                # Specify dtype for ID to avoid issues
                self.df_log = pd.read_excel(filepath, dtype={'ID': str})
                # Ensure base columns exist
                for col in config.LOG_BASE_COLUMNS:
                     if col not in self.df_log.columns:
                         logger.warning(f"Column '{col}' missing in log file '{filepath}'. Adding.")
                         self.df_log[col] = None
                self.df_log['ID'] = self.df_log['ID'].astype(str)

            # Ensure all day columns exist for the month (using parsed target_date)
            if target_date and self.df_log is not None:
                _, num_days = calendar.monthrange(target_date.year, target_date.month)
                for day in range(1, num_days + 1):
                    col_name = f"Ngày {day}"
                    if col_name not in self.df_log.columns:
                        self.df_log[col_name] = None # Add missing day columns

            logger.info(f"Successfully loaded/created OT log file: {filepath}")
            return self.df_log

        except Exception as e:
            logger.error(f"Error loading/creating OT log file '{filepath}': {e}", exc_info=True)
            # Return an empty DataFrame or handle error appropriately
            self.df_log = None # Indicate failure
            # Optionally create an empty structure on error?
            # if target_date:
            #    self.df_log = self._create_new_log_sheet(target_date)
            return None

    def _create_new_log_sheet(self, target_date):
        year, month = target_date.year, target_date.month
        _, num_days = calendar.monthrange(year, month)
        day_columns = [f"Ngày {day}" for day in range(1, num_days + 1)]
        columns = config.LOG_BASE_COLUMNS + day_columns
        df = pd.DataFrame(columns=columns)
        # Set dtype for ID column specifically if creating empty
        df['ID'] = df['ID'].astype(str)
        return df

    def save_log(self):
        if self.df_log is None or self.current_log_filepath is None:
            logger.error("No log data or filepath to save.")
            return
        try:
            # Ensure directory exists
            log_folder = os.path.dirname(self.current_log_filepath)
            os.makedirs(log_folder, exist_ok=True)

            # --- Add float_format parameter ---
            self.df_log.to_excel(
                self.current_log_filepath,
                index=False,
                float_format="%.2f"  # Format floats to 2 decimal places when writing
            )
            # --- End modification ---

            logger.info(f"OT log saved to '{self.current_log_filepath}'")
        except Exception as e:
            logger.error(f"Error saving OT log '{self.current_log_filepath}': {e}", exc_info=True)
            # Notify UI

    def _ensure_employee_rows_exist(self, employee_info):
        emp_id = str(employee_info['ID'])
        if self.df_log is None:
            logger.error("Log DataFrame not loaded.")
            return -1 # Indicate error

        # Check if employee ID exists in the log
        existing_rows = self.df_log[self.df_log['ID'] == emp_id]

        if existing_rows.empty:
            # Add 3 new rows for the employee
            next_stt = self.df_log['STT'].max() + 1 if 'STT' in self.df_log.columns and not self.df_log.empty else 1
            new_rows_data = []
            for row_type in config.LOG_ROW_TYPES:
                 new_row = {
                     'STT': next_stt,
                     'Họ tên': employee_info['Họ tên'],
                     'ID': emp_id,
                     # Initialize day columns potentially?
                 }
                 # Add placeholder for row type identification if needed, or rely on order
                 # For simplicity, we'll find the row index based on ID and the known order later
                 new_rows_data.append(new_row)

            # Create a temporary DataFrame for new rows
            # Important: Define columns explicitly to match self.df_log
            new_rows_df = pd.DataFrame(new_rows_data, columns=self.df_log.columns)

            # Concatenate
            self.df_log = pd.concat([self.df_log, new_rows_df], ignore_index=True)
            logger.info(f"Added log entry structure for employee ID: {emp_id}")
            # Find the index of the first new row (Giờ Vào)
            # Re-query after concat might be safer
            existing_rows = self.df_log[self.df_log['ID'] == emp_id]
            if not existing_rows.empty:
                 return existing_rows.index[0] # Return index of the 'Giờ Vào' row
            else:
                 logger.error(f"Failed to find rows immediately after adding for employee ID: {emp_id}")
                 return -1 # Error
        else:
            # Return the index of the first row ('Giờ Vào') for this employee
            return existing_rows.index[0]

    def write_log_entry(self, employee_info, entry_datetime, entry_type, value):
        target_date = entry_datetime.date()
        required_log_filepath = self._get_log_filepath(entry_datetime) # Get the path needed

        # Check if the required log file is correctly loaded
        if required_log_filepath != self.current_log_filepath or self.df_log is None:
            logger.info(f"Log file needs loading/reloading for date {target_date}. Required: {required_log_filepath}")
            if self.df_log is not None: # Save current log if it exists and is different
                 self.save_log()
            # Load the correct file using the specific path
            if self._load_log_file(required_log_filepath) is None:
                 logger.error(f"Failed to load required log file {required_log_filepath}. Cannot write entry.")
                 return False # Indicate failure

        # Now self.df_log should be the correct one
        if self.df_log is None:
             logger.error("Cannot write log entry, log data frame is None after load attempt.")
             return False

        emp_id = str(employee_info['ID'])
        day_column = f"Ngày {target_date.day}"

        # Ensure the day column exists (should be handled by _load_log_for_date, but double-check)
        if day_column not in self.df_log.columns:
            logger.error(f"Day column '{day_column}' does not exist in the log file '{self.current_log_filepath}'.")
            return False

        base_row_index = self._ensure_employee_rows_exist(employee_info)
        if base_row_index == -1:
             logger.error(f"Could not find or create rows for employee ID: {emp_id}")
             return False

        try:
            row_offset = config.LOG_ROW_TYPES.index(entry_type)
            target_row_index = base_row_index + row_offset
        except (ValueError, IndexError):
            logger.error(f"Invalid log entry type or row index calculation: {entry_type}")
            return False

        try:
            self.df_log.loc[target_row_index, day_column] = value
            logger.info(f"Logged '{entry_type}' for Emp ID {emp_id} on {target_date.day}: {value} in {self.current_log_filepath}")
            self.save_log() # Save after each write
            return True
        except Exception as e:
            logger.error(f"Failed to write log entry at row {target_row_index}, col '{day_column}': {e}", exc_info=True)
            return False


    def get_monthly_ot_minutes(self, emp_id, target_date):
        """
        Calculates total OT minutes for a given employee in the specified month.
        Reads logged hours from the 'Tổng thời gian' row and converts back to minutes.
        """ # Updated docstring
        required_log_filepath = self._get_log_filepath(target_date)
        # Ensure correct month's log is loaded
        if required_log_filepath != self.current_log_filepath or self.df_log is None:
             logger.info(f"Loading log file {required_log_filepath} for get_monthly_ot_minutes")
             if self._load_log_file(required_log_filepath) is None:
                  logger.warning(f"Could not load log file {required_log_filepath} for OT calculation.")
                  return 0 # Cannot calculate if log doesn't load

        if self.df_log is None:
            logger.warning("Log DataFrame is None in get_monthly_ot_minutes.")
            return 0

        emp_id_str = str(emp_id)
        emp_rows = self.df_log[self.df_log['ID'] == emp_id_str]

        if emp_rows.empty:
            # logger.debug(f"Employee {emp_id_str} not found in log {os.path.basename(required_log_filepath)} for OT calculation.")
            return 0 # Employee not in this month's log yet

        # Find the 'Tổng thời gian' row for this employee
        try:
            base_index = emp_rows.index[0]
            total_time_row_index = base_index + config.LOG_ROW_TYPES.index('Tổng thời gian')
            # Check if index exists before accessing .loc
            if total_time_row_index not in self.df_log.index:
                 logger.warning(f"Could not find 'Tổng thời gian' row structure (Index {total_time_row_index}) for employee ID {emp_id_str} in {os.path.basename(required_log_filepath)}")
                 return 0
            total_time_row = self.df_log.loc[total_time_row_index]
        except (IndexError, ValueError):
             logger.error(f"Error finding 'Tổng thời gian' row structure for employee ID {emp_id_str} in {os.path.basename(required_log_filepath)}")
             return 0

        total_minutes = 0.0 # Use float for accumulation
        _, num_days = calendar.monthrange(target_date.year, target_date.month)
        day_columns = [f"Ngày {day}" for day in range(1, num_days + 1)]

        for col in day_columns:
            if col in total_time_row.index:
                value = total_time_row[col] # This value should be OT hours
                # Check if value is a number (int or float)
                if pd.notna(value) and isinstance(value, (int, float)):
                    try:
                        # --- CHANGE HERE: Convert logged hours back to minutes ---
                        ot_hours = float(value)
                        total_minutes += (ot_hours * 60.0)
                        # --- END CHANGE ---
                    except ValueError:
                         logger.warning(f"Could not convert value '{value}' to float for OT hours in Col {col}, Emp ID {emp_id_str}. Skipping.")
                elif pd.notna(value):
                     logger.warning(f"Non-numeric value '{value}' found in 'Tổng thời gian' for Emp ID {emp_id_str}, Col {col}. Skipping.")

        # Return total accumulated minutes (can be float, comparison logic should handle it)
        # Rounding here might hide small discrepancies, better to compare floats or round at comparison point.
        logger.debug(f"Calculated total OT minutes for Emp ID {emp_id_str} in {target_date.strftime('%m/%Y')}: {total_minutes}")
        return total_minutes

    def create_next_month_log(self):
        today = datetime.now()
        first_day_of_current_month = today.replace(day=1)
        # Go to the last day of the current month, then add one day
        last_day_of_current_month = first_day_of_current_month.replace(day=calendar.monthrange(today.year, today.month)[1])
        first_day_of_next_month = last_day_of_current_month + timedelta(days=1)

        next_month_filepath = self._get_log_filepath(first_day_of_next_month)

        if os.path.exists(next_month_filepath):
            logger.info(f"Log file for next month '{next_month_filepath}' already exists.")
            return True, f"File log tháng {first_day_of_next_month.strftime('%m/%Y')} đã tồn tại."
        else:
            try:
                # Create the empty structure
                df_next = self._create_new_log_sheet(first_day_of_next_month)
                # Ensure directory exists
                os.makedirs(os.path.dirname(next_month_filepath), exist_ok=True)
                df_next.to_excel(next_month_filepath, index=False)
                logger.info(f"Created log file for next month: {next_month_filepath}")
                return True, f"Đã tạo file log tháng {first_day_of_next_month.strftime('%m/%Y')}."
            except Exception as e:
                logger.error(f"Failed to create next month's log file '{next_month_filepath}': {e}")
                return False, f"Lỗi khi tạo file log: {e}"

    def backup_current_log(self):
        if not self.current_log_filepath or not os.path.exists(self.current_log_filepath):
            logger.warning("Current log file does not exist or is not loaded. Cannot backup.")
            return

        backup_folder = config.get_backup_folder(self.settings_manager, type="log")
        timestamp = datetime.now().strftime(config.BACKUP_TIMESTAMP_FORMAT)
        log_filename = os.path.basename(self.current_log_filepath)
        backup_filename = f"{os.path.splitext(log_filename)[0]}_{timestamp}.xlsx"
        backup_filepath = os.path.join(backup_folder, backup_filename)

        try:
            shutil.copy2(self.current_log_filepath, backup_filepath)
            logger.info(f"Log file '{log_filename}' backed up successfully to '{backup_filepath}'")
        except Exception as e:
            logger.error(f"Failed to backup log file '{self.current_log_filepath}' to '{backup_filepath}': {e}")