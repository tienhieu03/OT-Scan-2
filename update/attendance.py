# attendance_manager.py
# ... (imports) ...

class AttendanceManager:
    # ... (__init__) ...

    def process_swipe(self, card_id):
        self._reset_daily_state_if_needed()
        now = datetime.now()
        today = now.date()
        card_id = str(card_id).strip()

        logger.info(f"Processing swipe for CARD ID: {card_id} at {now}")

        # ... (Swipe Delay Check) ...
        # ... (Find Employee) ...
        # ... (Handle New Employee) ...

        # --- MODIFY: Get Active Shift Info ---
        try:
            # Use the new method to get times for the currently selected active shift
            shift_start_time, shift_end_time = self.settings_manager.get_active_shift_times()
        except Exception as e:
             logger.error(f"Could not get active shift times: {e}. Aborting swipe processing.", exc_info=True)
             # Optionally update UI status here
             # self.ui_update_callback(status="Lỗi lấy thông tin ca làm việc")
             return # Stop processing if shift info is unavailable
        # --- END MODIFY ---

        allowed_window = self.settings_manager.get_allowed_swipe_window()
        shift_start_dt_today = datetime.combine(today, shift_start_time)
        earliest_clock_in = shift_start_dt_today - allowed_window
        shift_end_dt_today = datetime.combine(today, shift_end_time)

        # ... (Rest of the logic for determining swipe type, validation, logging, OT calc remains the same)
        # It will now use the start/end times of the currently ACTIVE shift.
        # The _calculate_and_log_ot method also needs to fetch the active shift times again
        # or we need to pass them down. Let's fetch again for simplicity for now.

    def _calculate_and_log_ot(self, card_id, employee_info, clock_out_time):
        # ... (get clock_in_time, emp_id, emp_name, today) ...

        # --- MODIFY: Get Active Shift Info Again ---
        try:
            shift_start_time, shift_end_time = self.settings_manager.get_active_shift_times()
        except Exception as e:
             logger.error(f"Could not get active shift times for OT calculation: {e}. Cannot calculate OT.", exc_info=True)
             # Update UI?
             self.ui_update_callback(status=f"Lỗi tính OT (Ca làm việc?) ({employee_info.get('Họ tên', '')})", card_id=card_id, name=employee_info.get('Họ tên'), emp_id=employee_info.get('ID'), time=clock_out_time)
             return
        # --- END MODIFY ---

        shift_start_dt = datetime.combine(today, shift_start_time)
        shift_end_dt = datetime.combine(today, shift_end_time)

        # ... (Rest of the OT calculation logic using shift_start_dt, shift_end_dt remains the same) ...
        # ... (Limit checking using get_monthly_ot_minutes remains the same) ...
        # ... (Logging OT hours remains the same) ...

    # ... (dummy_ui_update if kept) ...