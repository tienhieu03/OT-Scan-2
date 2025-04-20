# ui_manager.py
import customtkinter as ctk
from tkinter import messagebox, filedialog, simpledialog
from datetime import datetime, time # Ensure time is imported
import config
import logging
from collections import deque
import os

logger = logging.getLogger(__name__)

class UIManager(ctk.CTk):
    def __init__(self, attendance_manager, settings_manager, employee_manager, ot_log_manager):
        super().__init__()

        self.attendance_manager = attendance_manager
        self.settings_manager = settings_manager
        self.employee_manager = employee_manager
        self.ot_log_manager = ot_log_manager

        self.title(config.APP_TITLE)
        self.geometry("800x850") # Increased height significantly
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # Data for display
        self.last_card_id = ctk.StringVar(value="---")
        self.last_name = ctk.StringVar(value="---")
        # ... other display vars ...
        self.current_status = ctk.StringVar(value="Sẵn sàng")
        self.log_messages = deque(maxlen=config.MAX_LOG_DISPLAY_ENTRIES)

        # Settings control
        self.settings_editing_enabled = ctk.BooleanVar(value=False)
        self.active_shift_var = ctk.StringVar() # Variable for active shift dropdown

        # Dictionary to hold shift entry widgets {shift_name: {"start": entry, "end": entry}}
        self.shift_entries = {}

        self._create_widgets()
        self._load_settings_to_ui() # Load includes populating shift entries/dropdown
        self._update_settings_widgets_state() # Set initial state

        self._update_clock()
        self.after(250, self._refocus_hidden_entry)

    def _create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # Log area

        # --- Top Frame: Last Swipe Info ---
        # ... (remains the same) ...

        # --- Middle Frame: Log Display ---
        # ... (remains the same) ...

        # --- Bottom Frame: Tabs (Settings) ---
        # Increased height needed for the new shift tab content
        tab_view = ctk.CTkTabview(self, height=410)
        tab_view.grid(row=2, column=0, padx=10, pady=(0,10), sticky="nsew")
        tab_view.add("Ca & Folder") # Renamed for brevity
        tab_view.add("Ca làm việc") # New Shift Tab
        tab_view.add("Thiết bị")
        tab_view.add("Thao tác Log")

        # --- Settings Tab 1: General (Old Ca & Folder) ---
        settings_tab_general = tab_view.tab("Ca & Folder")
        settings_tab_general.grid_columnconfigure(1, weight=1)
        # REMOVE Shift Time entries from here
        # Swipe Delay
        ctk.CTkLabel(settings_tab_general, text="Delay giữa 2 lần quẹt (phút):").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.swipe_delay_entry = ctk.CTkEntry(settings_tab_general, width=100)
        self.swipe_delay_entry.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        # Database Folder
        ctk.CTkLabel(settings_tab_general, text="Thư mục Database NV:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.db_folder_label = ctk.CTkLabel(settings_tab_general, text="...", width=300, anchor="w")
        self.db_folder_label.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.db_folder_button = ctk.CTkButton(settings_tab_general, text="Chọn...", command=self._select_db_folder, width=80)
        self.db_folder_button.grid(row=1, column=2, padx=5, pady=5)
        # Log Folder
        ctk.CTkLabel(settings_tab_general, text="Thư mục Log OT:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.log_folder_label = ctk.CTkLabel(settings_tab_general, text="...", width=300, anchor="w")
        self.log_folder_label.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        self.log_folder_button = ctk.CTkButton(settings_tab_general, text="Chọn...", command=self._select_log_folder, width=80)
        self.log_folder_button.grid(row=2, column=2, padx=5, pady=5)


        # --- Settings Tab 2: Shifts ---
        settings_tab_shifts = tab_view.tab("Ca làm việc")
        settings_tab_shifts.grid_columnconfigure((1, 2), weight=1) # Configure columns for entries

        # Active Shift Selection
        ctk.CTkLabel(settings_tab_shifts, text="Ca làm việc đang áp dụng:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        # Get initial shift names for the dropdown
        initial_shift_names = self.settings_manager.get_shift_names()
        if not initial_shift_names: initial_shift_names = ["(No Shifts Defined)"] # Placeholder
        self.active_shift_dropdown = ctk.CTkOptionMenu(
            settings_tab_shifts,
            variable=self.active_shift_var,
            values=initial_shift_names
        )
        self.active_shift_dropdown.grid(row=0, column=1, columnspan=2, padx=10, pady=(10, 5), sticky="ew")

        # Header Row for Shift Entries
        ctk.CTkLabel(settings_tab_shifts, text="Tên Ca", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(settings_tab_shifts, text="Giờ Bắt Đầu (HH:MM)", font=ctk.CTkFont(weight="bold")).grid(row=1, column=1, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(settings_tab_shifts, text="Giờ Kết Thúc (HH:MM)", font=ctk.CTkFont(weight="bold")).grid(row=1, column=2, padx=10, pady=5, sticky="w")

        # Create entries for each default shift (names are fixed for now)
        self.shift_entries = {} # Reset dictionary
        current_row = 2
        # Use default shift names as keys, assuming they won't change easily
        default_shifts_config = config.DEFAULT_SHIFTS # Use the structure from config
        for shift_config in default_shifts_config:
             shift_name = shift_config["name"]
             # Shift Name Label (read-only for now)
             ctk.CTkLabel(settings_tab_shifts, text=shift_name).grid(row=current_row, column=0, padx=10, pady=5, sticky="w")

             # Start Time Entry
             start_entry = ctk.CTkEntry(settings_tab_shifts, width=100)
             start_entry.grid(row=current_row, column=1, padx=10, pady=5, sticky="w")

             # End Time Entry
             end_entry = ctk.CTkEntry(settings_tab_shifts, width=100)
             end_entry.grid(row=current_row, column=2, padx=10, pady=5, sticky="w")

             # Store entries associated with the shift name
             self.shift_entries[shift_name] = {"start": start_entry, "end": end_entry}
             current_row += 1


        # --- Settings Tab 3: Device ---
        settings_tab_device = tab_view.tab("Thiết bị")
        # ... (VID/PID entries remain the same) ...

        # --- Settings Tab 4: Log Actions ---
        log_actions_tab = tab_view.tab("Thao tác Log")
        # ... (remains the same) ...


        # --- Edit Switch and Save Button (Common) ---
        edit_save_frame = ctk.CTkFrame(self, fg_color="transparent")
        edit_save_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew") # Below tabview
        # ... (Switch and Save Button remain the same) ...

        # --- Bottom Status Bar ---
        self.status_bar = ctk.CTkLabel(self, text="Clock: --:--:-- | Input Status: Initializing...", anchor="w")
        self.status_bar.grid(row=4, column=0, padx=10, pady=(0,5), sticky="ew")

        # --- Hidden Swipe Entry ---
        # ... (remains the same) ...

    # ... (_update_clock, update_input_status, _refocus_hidden_entry, _on_swipe_input remain the same) ...

    def _load_settings_to_ui(self):
        # --- General Tab ---
        self.swipe_delay_entry.delete(0, ctk.END)
        self.swipe_delay_entry.insert(0, str(self.settings_manager.get_setting("swipe_delay_minutes", config.DEFAULT_SWIPE_DELAY_MINUTES)))
        self.db_folder_label.configure(text=self.settings_manager.get_setting("database_folder", config.DEFAULT_DATA_FOLDER))
        self.log_folder_label.configure(text=self.settings_manager.get_setting("log_folder", os.path.join(config.DEFAULT_DATA_FOLDER, config.DEFAULT_LOG_FOLDER_NAME)))

        # --- Shifts Tab ---
        # Load active shift
        active_shift = self.settings_manager.get_setting("active_shift_name", config.DEFAULT_ACTIVE_SHIFT_NAME)
        all_shift_names = self.settings_manager.get_shift_names()
        if not all_shift_names: all_shift_names = ["(No Shifts Defined)"]
        self.active_shift_dropdown.configure(values=all_shift_names) # Update dropdown values
        if active_shift in all_shift_names:
             self.active_shift_var.set(active_shift)
        elif all_shift_names:
             self.active_shift_var.set(all_shift_names[0]) # Default to first if active not found

        # Load individual shift times
        all_shifts_data = self.settings_manager.get_all_shifts()
        for shift_name, entries in self.shift_entries.items():
            # Find the data for this shift name
            shift_data = next((s for s in all_shifts_data if isinstance(s, dict) and s.get("name") == shift_name), None)
            start_time = shift_data.get("start", "00:00") if shift_data else "00:00"
            end_time = shift_data.get("end", "00:00") if shift_data else "00:00"

            entries["start"].delete(0, ctk.END)
            entries["start"].insert(0, start_time)
            entries["end"].delete(0, ctk.END)
            entries["end"].insert(0, end_time)

        # --- Device Tab ---
        self.vid_entry.delete(0, ctk.END)
        self.pid_entry.delete(0, ctk.END)
        vid = self.settings_manager.get_setting("zkteco_vid", config.DEFAULT_ZKTeco_VID)
        pid = self.settings_manager.get_setting("zkteco_pid", config.DEFAULT_ZKTeco_PID)
        self.vid_entry.insert(0, f"0x{vid:04X}")
        self.pid_entry.insert(0, f"0x{pid:04X}")


    def _update_settings_widgets_state(self):
        """Enables or disables settings widgets based on the switch state."""
        is_enabled = self.settings_editing_enabled.get()
        new_state = "normal" if is_enabled else "disabled"

        # General Tab Widgets
        self.swipe_delay_entry.configure(state=new_state)
        self.db_folder_button.configure(state=new_state)
        self.log_folder_button.configure(state=new_state)

        # Shifts Tab Widgets
        self.active_shift_dropdown.configure(state=new_state)
        for shift_name, entries in self.shift_entries.items():
            entries["start"].configure(state=new_state)
            entries["end"].configure(state=new_state)

        # Device Tab Widgets
        self.vid_entry.configure(state=new_state)
        self.pid_entry.configure(state=new_state)

        # Common Widgets
        self.save_settings_button.configure(state=new_state)
        # logger.debug(f"Settings edit mode: {'Enabled' if is_enabled else 'Disabled'}")


    def _select_db_folder(self):
        # ... (remains the same) ...
        pass

    def _select_log_folder(self):
        # ... (remains the same) ...
        pass

    def _save_settings(self):
        logger.info("Attempting to save settings...")
        vid_int, pid_int = None, None
        validated_shifts = [] # To store validated shift data

        # --- Validate General Tab Settings ---
        try:
            delay = int(self.swipe_delay_entry.get())
            if delay < 0: raise ValueError("Delay must be non-negative")
        except ValueError:
             messagebox.showerror("Lỗi Giá Trị", "Ca & Folder:\nDelay giữa 2 lần quẹt phải là một số nguyên không âm.")
             return

        # --- Validate Shifts Tab Settings ---
        active_shift_selection = self.active_shift_var.get()
        if not active_shift_selection or active_shift_selection == "(No Shifts Defined)":
             messagebox.showerror("Lỗi Giá Trị", "Ca làm việc:\nVui lòng chọn một ca làm việc đang áp dụng.")
             return

        try:
            for shift_name, entries in self.shift_entries.items():
                start_str = entries["start"].get().strip()
                end_str = entries["end"].get().strip()
                # Validate time format
                start_time_obj = datetime.strptime(start_str, "%H:%M").time()
                end_time_obj = datetime.strptime(end_str, "%H:%M").time()
                # Add validated data to list
                validated_shifts.append({"name": shift_name, "start": start_str, "end": end_str})
        except ValueError:
            messagebox.showerror("Lỗi Định Dạng", f"Ca làm việc:\nGiờ bắt đầu hoặc kết thúc cho ca '{shift_name}' không đúng định dạng HH:MM.")
            return

        # --- Validate Device Tab Settings ---
        try:
            vid_str = self.vid_entry.get().strip()
            pid_str = self.pid_entry.get().strip()
            if not vid_str or not pid_str: raise ValueError("VID và PID không được để trống.")
            vid_int = int(vid_str, 0)
            pid_int = int(pid_str, 0)
            if vid_int < 0 or pid_int < 0 or vid_int > 0xFFFF or pid_int > 0xFFFF:
                 raise ValueError("VID/PID phải là giá trị 16-bit không âm (0 - 65535).")
        except ValueError as e:
             messagebox.showerror("Lỗi Giá Trị", f"Thiết bị:\nLỗi định dạng VID hoặc PID.\n{e}\nHãy nhập số thập phân (e.g., 6997) hoặc hexa (e.g., 0x1b55).")
             return

        # --- All Validations Passed - Save Settings ---
        self.settings_manager.set_setting("swipe_delay_minutes", int(self.swipe_delay_entry.get()))
        self.settings_manager.set_setting("database_folder", self.db_folder_label.cget("text"))
        self.settings_manager.set_setting("log_folder", self.log_folder_label.cget("text"))
        self.settings_manager.set_setting("active_shift_name", active_shift_selection)
        self.settings_manager.set_setting("shifts", validated_shifts) # Save the list of dicts
        self.settings_manager.set_setting("zkteco_vid", vid_int)
        self.settings_manager.set_setting("zkteco_pid", pid_int)

        self.settings_manager.save_settings()

        # --- Reload dependent components ---
        try:
            logger.info("Reloading employee database after settings save...")
            self.employee_manager._load_database()
            logger.info("Reloading current OT log file after settings save...")
            current_log_path = self.ot_log_manager._get_log_filepath(datetime.now())
            self.ot_log_manager._load_log_file(current_log_path)
            logger.info(f"Successfully reloaded log file: {current_log_path}")
            # Update dropdown values in case they changed (though names are fixed now)
            self.active_shift_dropdown.configure(values=self.settings_manager.get_shift_names())

        except AttributeError as ae:
             logger.error(f"AttributeError reloading data after settings change: {ae}", exc_info=True)
             messagebox.showwarning("Lỗi Tải Dữ liệu (Code)", f"Đã lưu cài đặt, nhưng có lỗi khi tải lại dữ liệu:\n{ae}\n\nCó thể do cập nhật code. Vui lòng khởi động lại ứng dụng.")
        except Exception as e:
             logger.error(f"Error reloading data after settings change: {e}", exc_info=True)
             messagebox.showwarning("Lỗi Tải Dữ liệu", f"Đã lưu cài đặt, nhưng có lỗi khi tải lại dữ liệu:\n{e}\n\nVui lòng khởi động lại ứng dụng nếu gặp sự cố.")

        # --- User Feedback ---
        messagebox.showinfo("Thành công", "Đã lưu cài đặt.\n\nLƯU Ý: Nếu bạn đã thay đổi VID/PID, cần khởi động lại ứng dụng để thay đổi có hiệu lực.")

        # Disable editing mode
        self.settings_editing_enabled.set(False)
        self._update_settings_widgets_state()

    # ... (rest of UIManager: _create_next_month_log, _add_log_message, update_display, ask_new_employee_info, run) ...