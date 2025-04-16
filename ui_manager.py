# ui_manager.py
import customtkinter as ctk
from tkinter import messagebox, filedialog, simpledialog
from datetime import datetime
import config
import logging
from collections import deque
import os
import queue

logger = logging.getLogger(__name__)

class UIManager(ctk.CTk):
    def __init__(self, attendance_manager, settings_manager, employee_manager, ot_log_manager, hid_queue):
        super().__init__()

        self.attendance_manager = attendance_manager
        self.settings_manager = settings_manager
        self.employee_manager = employee_manager
        self.ot_log_manager = ot_log_manager
        self.hid_queue = hid_queue

        self.title(config.APP_TITLE)
        self.geometry("800x750") # Increased height further for VID/PID
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # Data for display
        self.last_card_id = ctk.StringVar(value="---")
        self.last_name = ctk.StringVar(value="---")
        self.last_emp_id = ctk.StringVar(value="---")
        self.last_time = ctk.StringVar(value="---")
        self.current_status = ctk.StringVar(value="Sẵn sàng")
        self.log_messages = deque(maxlen=config.MAX_LOG_DISPLAY_ENTRIES)

        # Variable to control settings edit mode
        self.settings_editing_enabled = ctk.BooleanVar(value=False)

        # Build UI
        self._create_widgets()
        self._load_settings_to_ui()
        self._update_settings_widgets_state()

        # Start polling the HID queue
        self.after(100, self._check_hid_queue)
        # Start clock update
        self._update_clock()

    def _create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # Allow log area to expand

        # --- Top Frame: Last Swipe Info ---
        top_frame = ctk.CTkFrame(self, corner_radius=10)
        top_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        top_frame.grid_columnconfigure((1, 3, 5), weight=1)

        ctk.CTkLabel(top_frame, text="CARD ID:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(top_frame, textvariable=self.last_card_id, width=120).grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(top_frame, text="Họ tên:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(top_frame, textvariable=self.last_name, width=150).grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(top_frame, text="ID NV:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=4, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(top_frame, textvariable=self.last_emp_id, width=100).grid(row=0, column=5, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(top_frame, text="Thời gian:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(top_frame, textvariable=self.last_time).grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(top_frame, text="Trạng thái:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=2, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(top_frame, textvariable=self.current_status, width=250, anchor="w").grid(row=1, column=3, columnspan=3, padx=5, pady=5, sticky="ew")

        # --- Middle Frame: Log Display ---
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        self.log_textbox = ctk.CTkTextbox(log_frame, state="disabled", wrap="word", corner_radius=0)
        self.log_textbox.grid(row=0, column=0, sticky="nsew")

        # --- Bottom Frame: Tabs (Settings) ---
        tab_view = ctk.CTkTabview(self, height=310) # Increased height
        tab_view.grid(row=2, column=0, padx=10, pady=(0,10), sticky="ew")
        tab_view.add("Cài đặt Ca & Folder")
        tab_view.add("Cài đặt Thiết bị") # New Tab for VID/PID
        tab_view.add("Thao tác Log")

        # --- Settings Tab 1: Shift & Folders ---
        settings_tab_folders = tab_view.tab("Cài đặt Ca & Folder")
        settings_tab_folders.grid_columnconfigure(1, weight=1)

        # Shift Time
        ctk.CTkLabel(settings_tab_folders, text="Giờ bắt đầu ca (HH:MM):").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.shift_start_entry = ctk.CTkEntry(settings_tab_folders, width=100)
        self.shift_start_entry.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(settings_tab_folders, text="Giờ kết thúc ca (HH:MM):").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.shift_end_entry = ctk.CTkEntry(settings_tab_folders, width=100)
        self.shift_end_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # Swipe Delay
        ctk.CTkLabel(settings_tab_folders, text="Delay giữa 2 lần quẹt (phút):").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.swipe_delay_entry = ctk.CTkEntry(settings_tab_folders, width=100)
        self.swipe_delay_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        # Database Folder
        ctk.CTkLabel(settings_tab_folders, text="Thư mục Database NV:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.db_folder_label = ctk.CTkLabel(settings_tab_folders, text="...", width=300, anchor="w")
        self.db_folder_label.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        self.db_folder_button = ctk.CTkButton(settings_tab_folders, text="Chọn...", command=self._select_db_folder, width=80)
        self.db_folder_button.grid(row=3, column=2, padx=5, pady=5)

        # Log Folder
        ctk.CTkLabel(settings_tab_folders, text="Thư mục Log OT:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.log_folder_label = ctk.CTkLabel(settings_tab_folders, text="...", width=300, anchor="w")
        self.log_folder_label.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        self.log_folder_button = ctk.CTkButton(settings_tab_folders, text="Chọn...", command=self._select_log_folder, width=80)
        self.log_folder_button.grid(row=4, column=2, padx=5, pady=5)

        # --- Settings Tab 2: Device Settings (VID/PID) ---
        settings_tab_device = tab_view.tab("Cài đặt Thiết bị")
        settings_tab_device.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(settings_tab_device, text="ZKTeco Vendor ID (VID):", anchor="w").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.vid_entry = ctk.CTkEntry(settings_tab_device, placeholder_text="e.g., 0x1b55", width=150)
        self.vid_entry.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(settings_tab_device, text="ZKTeco Product ID (PID):", anchor="w").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.pid_entry = ctk.CTkEntry(settings_tab_device, placeholder_text="e.g., 0xb502", width=150)
        self.pid_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(settings_tab_device, text="(Nhập dạng số thập phân hoặc hexa '0x...')", text_color="gray", font=ctk.CTkFont(size=10)).grid(row=2, column=0, columnspan=2, padx=10, pady=(0,10), sticky="w")
        ctk.CTkLabel(settings_tab_device, text="LƯU Ý: Cần khởi động lại ứng dụng\nđể thay đổi VID/PID có hiệu lực.", text_color="orange", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="w")


        # --- Edit Switch and Save Button ---
        edit_save_frame = ctk.CTkFrame(self, fg_color="transparent")
        edit_save_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew") # Position below tabview
        edit_save_frame.grid_columnconfigure(1, weight=1)

        self.edit_switch = ctk.CTkSwitch(
            edit_save_frame,
            text="Cho phép sửa cài đặt",
            variable=self.settings_editing_enabled,
            onvalue=True,
            offvalue=False,
            command=self._update_settings_widgets_state
        )
        self.edit_switch.grid(row=0, column=0, padx=(0, 20), pady=5, sticky="w")

        self.save_settings_button = ctk.CTkButton(edit_save_frame, text="Lưu Tất Cả Cài Đặt", command=self._save_settings)
        self.save_settings_button.grid(row=0, column=2, padx=5, pady=5, sticky="e")


        # --- Settings Tab 3: Log Actions ---
        log_actions_tab = tab_view.tab("Thao tác Log")
        log_actions_tab.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(log_actions_tab, text="Tạo File Log Tháng Tiếp Theo", command=self._create_next_month_log).grid(row=0, column=0, padx=10, pady=10)


        # --- Bottom Status Bar ---
        self.status_bar = ctk.CTkLabel(self, text="Clock: --:--:-- | HID Status: Initializing...", anchor="w")
        self.status_bar.grid(row=4, column=0, padx=10, pady=(0,5), sticky="ew") # Adjust row

    def _update_clock(self):
        """Updates the clock in the status bar every second."""
        now = datetime.now().strftime("%H:%M:%S")
        current_status_text = self.status_bar.cget("text")
        hid_part = current_status_text.split("|")[-1].strip()
        self.status_bar.configure(text=f"Clock: {now} | {hid_part}")
        self.after(1000, self._update_clock)

    def update_hid_status(self, status_message):
         """Updates the HID status part of the status bar."""
         current_status_text = self.status_bar.cget("text")
         clock_part = current_status_text.split("|")[0].strip()
         self.status_bar.configure(text=f"{clock_part} | HID Status: {status_message}")

    def _load_settings_to_ui(self):
        # Clear existing content
        self.shift_start_entry.delete(0, ctk.END)
        self.shift_end_entry.delete(0, ctk.END)
        self.swipe_delay_entry.delete(0, ctk.END)
        self.vid_entry.delete(0, ctk.END)
        self.pid_entry.delete(0, ctk.END)

        # Load Folder/Shift settings
        self.shift_start_entry.insert(0, self.settings_manager.get_setting("shift_start", config.DEFAULT_SHIFT_START))
        self.shift_end_entry.insert(0, self.settings_manager.get_setting("shift_end", config.DEFAULT_SHIFT_END))
        self.swipe_delay_entry.insert(0, str(self.settings_manager.get_setting("swipe_delay_minutes", config.DEFAULT_SWIPE_DELAY_MINUTES)))
        self.db_folder_label.configure(text=self.settings_manager.get_setting("database_folder", config.DEFAULT_DATA_FOLDER))
        self.log_folder_label.configure(text=self.settings_manager.get_setting("log_folder", os.path.join(config.DEFAULT_DATA_FOLDER, config.DEFAULT_LOG_FOLDER_NAME)))

        # Load VID/PID settings (display as hex)
        vid = self.settings_manager.get_setting("zkteco_vid", config.DEFAULT_ZKTeco_VID)
        pid = self.settings_manager.get_setting("zkteco_pid", config.DEFAULT_ZKTeco_PID)
        self.vid_entry.insert(0, hex(vid)) # Display as hex string e.g., "0x1b55"
        self.pid_entry.insert(0, hex(pid)) # Display as hex string e.g., "0xb502"


    def _update_settings_widgets_state(self):
        """Enables or disables settings widgets based on the switch state."""
        is_enabled = self.settings_editing_enabled.get()
        new_state = "normal" if is_enabled else "disabled"

        # Tab 1 Widgets
        self.shift_start_entry.configure(state=new_state)
        self.shift_end_entry.configure(state=new_state)
        self.swipe_delay_entry.configure(state=new_state)
        self.db_folder_button.configure(state=new_state)
        self.log_folder_button.configure(state=new_state)

        # Tab 2 Widgets (VID/PID)
        self.vid_entry.configure(state=new_state)
        self.pid_entry.configure(state=new_state)

        # Common Widgets
        self.save_settings_button.configure(state=new_state)

        logger.debug(f"Settings edit mode: {'Enabled' if is_enabled else 'Disabled'}")


    def _select_db_folder(self):
        # This button is only clickable when editing is enabled
        folder_selected = filedialog.askdirectory(initialdir=self.settings_manager.get_setting("database_folder"))
        if folder_selected:
            self.db_folder_label.configure(text=folder_selected)

    def _select_log_folder(self):
        # This button is only clickable when editing is enabled
        folder_selected = filedialog.askdirectory(initialdir=self.settings_manager.get_setting("log_folder"))
        if folder_selected:
            self.log_folder_label.configure(text=folder_selected)

    def _save_settings(self):
        logger.info("Attempting to save settings...")
        vid_int, pid_int = None, None # For storing validated integer values

        # --- Validate Tab 1 Settings ---
        try:
            datetime.strptime(self.shift_start_entry.get(), "%H:%M")
            datetime.strptime(self.shift_end_entry.get(), "%H:%M")
        except ValueError:
            messagebox.showerror("Lỗi Định Dạng", "Cài đặt Ca & Folder:\nGiờ bắt đầu hoặc kết thúc ca không đúng định dạng HH:MM.")
            return
        try:
            delay = int(self.swipe_delay_entry.get())
            if delay < 0: raise ValueError("Delay must be non-negative")
        except ValueError:
             messagebox.showerror("Lỗi Giá Trị", "Cài đặt Ca & Folder:\nDelay giữa 2 lần quẹt phải là một số nguyên không âm.")
             return

        # --- Validate Tab 2 Settings (VID/PID) ---
        try:
            vid_str = self.vid_entry.get().strip()
            pid_str = self.pid_entry.get().strip()
            if not vid_str or not pid_str:
                 raise ValueError("VID và PID không được để trống.")
            # int(value, 0) automatically detects base (e.g., 0x for hex)
            vid_int = int(vid_str, 0)
            pid_int = int(pid_str, 0)
            if vid_int < 0 or pid_int < 0 or vid_int > 0xFFFF or pid_int > 0xFFFF:
                 raise ValueError("VID/PID phải là giá trị 16-bit không âm (0 - 65535).")
        except ValueError as e:
             messagebox.showerror("Lỗi Giá Trị", f"Cài đặt Thiết bị:\nLỗi định dạng VID hoặc PID.\n{e}\nHãy nhập số thập phân (e.g., 6997) hoặc hexa (e.g., 0x1b55).")
             return

        # --- All Validations Passed - Save Settings ---
        self.settings_manager.set_setting("shift_start", self.shift_start_entry.get())
        self.settings_manager.set_setting("shift_end", self.shift_end_entry.get())
        self.settings_manager.set_setting("swipe_delay_minutes", int(self.swipe_delay_entry.get()))
        self.settings_manager.set_setting("database_folder", self.db_folder_label.cget("text"))
        self.settings_manager.set_setting("log_folder", self.log_folder_label.cget("text"))
        # Save VID/PID as integers
        self.settings_manager.set_setting("zkteco_vid", vid_int)
        self.settings_manager.set_setting("zkteco_pid", pid_int)

        self.settings_manager.save_settings()

        # Reload dependent components (DB/Log paths might have changed)
        try:
            self.employee_manager._load_database()
            self.ot_log_manager._load_log_for_date(datetime.now())
        except Exception as e:
             logger.error(f"Error reloading data after settings change: {e}")
             messagebox.showwarning("Lỗi Tải Dữ liệu", f"Đã lưu cài đặt, nhưng có lỗi khi tải lại dữ liệu:\n{e}\n\nVui lòng khởi động lại ứng dụng nếu gặp sự cố.")

        # --- User Feedback ---
        messagebox.showinfo("Thành công", "Đã lưu cài đặt.\n\nLƯU Ý: Nếu bạn đã thay đổi VID/PID, cần khởi động lại ứng dụng để thay đổi có hiệu lực.")

        # Disable editing mode after successful save
        self.settings_editing_enabled.set(False)
        self._update_settings_widgets_state()


    def _create_next_month_log(self):
        success, message = self.ot_log_manager.create_next_month_log()
        if success:
            messagebox.showinfo("Thành công", message)
        else:
            messagebox.showerror("Lỗi", message)

    def _add_log_message(self, message):
        """Adds a message to the log display area."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.log_messages.appendleft(log_entry) # Add to the beginning

        # Update textbox
        self.log_textbox.configure(state="normal") # Enable writing
        self.log_textbox.delete("1.0", ctk.END) # Clear existing content
        self.log_textbox.insert("1.0", "\n".join(self.log_messages)) # Insert all messages
        self.log_textbox.configure(state="disabled") # Disable editing

    def update_display(self, status="", card_id=None, name=None, emp_id=None, time=None):
        """Updates the top display panel and adds a log message."""
        if card_id:
            self.last_card_id.set(card_id)
        if name:
            self.last_name.set(name)
        if emp_id:
            self.last_emp_id.set(emp_id)
        if time:
            self.last_time.set(time.strftime("%d/%m/%Y %H:%M:%S"))
        else:
            self.last_time.set(datetime.now().strftime("%d/%m/%Y %H:%M:%S")) # Show current time if specific time not given

        self.current_status.set(status)

        # Construct log message based on provided info
        log_msg = status
        details = []
        if card_id: details.append(f"Card: {card_id}")
        if name: details.append(f"Tên: {name}")
        if emp_id: details.append(f"ID: {emp_id}")
        if details:
            log_msg += f" ({', '.join(details)})"

        self._add_log_message(log_msg)
        logger.info(f"UI Update: {log_msg}") # Also log to file/console

    def ask_new_employee_info(self, card_id):
        """
        Pops up dialogs to get Name and ID for a new card.
        Returns (name, emp_id) or (None, None) if cancelled.
        """
        self.update_display(status=f"Thẻ mới: {card_id}. Nhập thông tin NV.", card_id=card_id)
        messagebox.showinfo("Nhân viên mới", f"Phát hiện thẻ mới chưa có trong database:\nCARD ID: {card_id}\nVui lòng nhập thông tin nhân viên.")

        name = None
        emp_id = None

        while not emp_id:
             emp_id_input = simpledialog.askstring("Nhập ID Nhân viên", f"Nhập ID cho nhân viên có CARD ID: {card_id}", parent=self)
             if emp_id_input is None: # User cancelled
                 messagebox.showwarning("Hủy bỏ", "Đã hủy thêm nhân viên mới.")
                 return None, None
             emp_id_input = emp_id_input.strip()
             if not emp_id_input:
                  messagebox.showwarning("Thiếu thông tin", "ID Nhân viên không được để trống.")
                  continue # Ask again
             # Check if ID already exists
             if self.employee_manager.find_employee_by_id(emp_id_input):
                  messagebox.showwarning("ID Trùng", f"ID nhân viên '{emp_id_input}' đã tồn tại. Vui lòng nhập ID khác.")
             else:
                  emp_id = emp_id_input # Valid ID

        while not name:
            name_input = simpledialog.askstring("Nhập Họ tên", f"Nhập Họ tên cho nhân viên có ID: {emp_id}", parent=self)
            if name_input is None: # User cancelled
                messagebox.showwarning("Hủy bỏ", "Đã hủy thêm nhân viên mới.")
                return None, None # Return None even if ID was entered
            name_input = name_input.strip()
            if not name_input:
                 messagebox.showwarning("Thiếu thông tin", "Họ tên không được để trống.")
            else:
                 name = name_input # Valid name

        return name, emp_id


    def _check_hid_queue(self):
        """Periodically check the queue for new card IDs from the HID handler."""
        try:
            while True: # Process all messages currently in the queue
                card_id = self.hid_queue.get_nowait()
                logger.info(f"Received card ID from queue: {card_id}")

                # --- Handle New Employee Registration Flow ---
                employee = self.employee_manager.find_employee_by_card_id(card_id)
                if not employee:
                    name, emp_id = self.ask_new_employee_info(card_id)
                    if name and emp_id:
                        success, msg = self.employee_manager.add_employee(name, emp_id, card_id)
                        if success:
                            messagebox.showinfo("Thành công", f"Đã thêm nhân viên:\nTên: {name}\nID: {emp_id}\nCARD ID: {card_id}")
                            # Now process the swipe for the newly added employee
                            self.attendance_manager.process_swipe(card_id)
                        else:
                            messagebox.showerror("Lỗi", f"Không thể thêm nhân viên: {msg}")
                            self.update_display(status=f"Lỗi thêm NV ({card_id})", card_id=card_id)
                    else:
                        self.update_display(status=f"Đã hủy đăng ký thẻ ({card_id})", card_id=card_id)
                else:
                    self.attendance_manager.process_swipe(card_id)

        except queue.Empty:
            pass
        finally:
            self.after(100, self._check_hid_queue)

    def run(self):
        self.mainloop()