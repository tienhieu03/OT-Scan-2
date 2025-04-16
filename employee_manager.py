# employee_manager.py
import pandas as pd
import os
import shutil
from datetime import datetime
import config
import logging

logger = logging.getLogger(__name__)

class EmployeeManager:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        # Determine the path ONCE based on the provided settings manager
        self.db_filepath = config.get_db_filepath(self.settings_manager)
        logger.info(f"[EmployeeManager Init] Using DB Filepath: {self.db_filepath}") # Log path used
        self.df = self._load_database() 

    def _load_database(self):
        try:
            # Use the path determined during initialization
            if not os.path.exists(self.db_filepath):
                logger.warning(f"Database file '{self.db_filepath}' not found. Creating empty database.")
                df = pd.DataFrame(columns=config.DB_COLUMNS)
                df['CARD ID'] = df['CARD ID'].astype(str)
                # Ensure directory exists before saving
                os.makedirs(os.path.dirname(self.db_filepath) or '.', exist_ok=True)
                df.to_excel(self.db_filepath, index=False)
                return df
            else:
                logger.info(f"Loading database from: {self.db_filepath}")
                df = pd.read_excel(self.db_filepath, dtype={'CARD ID': str, 'ID': str})
                # ... (rest of loading logic remains the same) ...
                for col in config.DB_COLUMNS:
                    if col not in df.columns:
                        logger.warning(f"Column '{col}' missing in database. Adding.")
                        df[col] = None
                df['CARD ID'] = df['CARD ID'].astype(str)
                if 'STT' in df.columns and df['STT'].isnull().any():
                    df['STT'] = range(1, len(df) + 1)
                return df

        except FileNotFoundError:
             logger.error(f"Database file '{self.db_filepath}' not found during load.")
             return pd.DataFrame(columns=config.DB_COLUMNS, dtype={'CARD ID': str, 'ID': str})
        except Exception as e:
            logger.error(f"Error loading employee database '{self.db_filepath}': {e}", exc_info=True) # Log traceback
            return pd.DataFrame(columns=config.DB_COLUMNS, dtype={'CARD ID': str, 'ID': str})

    def save_database(self):
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_filepath) or '.', exist_ok=True)
            # Sort by STT before saving if column exists
            if 'STT' in self.df.columns:
                 self.df.sort_values(by='STT', inplace=True)
            self.df.to_excel(self.db_filepath, index=False)
            logger.info(f"Employee database saved to '{self.db_filepath}'")
        except Exception as e:
            logger.error(f"Error saving employee database '{self.db_filepath}': {e}")
            # Notify the user via UI

    def find_employee_by_card_id(self, card_id):
        if self.df.empty:
            return None
        # Ensure comparison is string vs string
        card_id_str = str(card_id).strip()
        result = self.df[self.df['CARD ID'] == card_id_str]
        if not result.empty:
            # Return first match as a dictionary
            return result.iloc[0].to_dict()
        return None

    def find_employee_by_id(self, emp_id):
        if self.df.empty:
            return None
        emp_id_str = str(emp_id).strip()
        result = self.df[self.df['ID'] == emp_id_str]
        if not result.empty:
            return result.iloc[0].to_dict()
        return None

    def add_employee(self, name, emp_id, card_id):
        card_id_str = str(card_id).strip()
        emp_id_str = str(emp_id).strip()

        if self.find_employee_by_card_id(card_id_str):
            logger.warning(f"Attempted to add employee with existing CARD ID: {card_id_str}")
            return False, "CARD ID đã tồn tại."
        if self.find_employee_by_id(emp_id_str):
            logger.warning(f"Attempted to add employee with existing ID: {emp_id_str}")
            return False, "ID nhân viên đã tồn tại."

        try:
            next_stt = self.df['STT'].max() + 1 if 'STT' in self.df.columns and not self.df.empty else 1
            new_employee = pd.DataFrame([{
                'STT': next_stt,
                'Họ tên': name,
                'ID': emp_id_str,
                'CARD ID': card_id_str
            }], columns=config.DB_COLUMNS)

            self.df = pd.concat([self.df, new_employee], ignore_index=True)
            self.save_database()
            logger.info(f"Added new employee: ID={emp_id_str}, Name={name}, CARD ID={card_id_str}")
            return True, "Thêm nhân viên thành công."
        except Exception as e:
            logger.error(f"Error adding employee: {e}")
            return False, f"Lỗi khi thêm nhân viên: {e}"

    def get_all_employees(self):
         # Return a list of dictionaries, ensure CARD ID and ID are strings
        if self.df.empty:
            return []
        # Reload to ensure freshness? Or assume df is up-to-date
        # self.df = self._load_database() # Uncomment if needed, but might impact performance
        df_copy = self.df.copy()
        df_copy['CARD ID'] = df_copy['CARD ID'].astype(str)
        df_copy['ID'] = df_copy['ID'].astype(str)
        return df_copy.to_dict('records')


    def backup_database(self):
        self.db_filepath = config.get_db_filepath(self.settings_manager) # Refresh path
        if not os.path.exists(self.db_filepath):
            logger.warning("Database file does not exist. Cannot backup.")
            return

        backup_folder = config.get_backup_folder(self.settings_manager, type="db")
        timestamp = datetime.now().strftime(config.BACKUP_TIMESTAMP_FORMAT)
        backup_filename = f"{os.path.splitext(config.DB_FILENAME)[0]}_{timestamp}.xlsx"
        backup_filepath = os.path.join(backup_folder, backup_filename)

        try:
            shutil.copy2(self.db_filepath, backup_filepath) # copy2 preserves metadata
            logger.info(f"Database backed up successfully to '{backup_filepath}'")
        except Exception as e:
            logger.error(f"Failed to backup database '{self.db_filepath}' to '{backup_filepath}': {e}")