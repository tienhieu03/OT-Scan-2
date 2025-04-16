# attendance_manager.py
from datetime import datetime, timedelta, time
import config
import logging

logger = logging.getLogger(__name__)

class AttendanceManager:
    def __init__(self, settings_manager, employee_manager, ot_log_manager, ui_update_callback):
        self.settings_manager = settings_manager
        self.employee_manager = employee_manager
        self.ot_log_manager = ot_log_manager
        self.ui_update_callback = ui_update_callback # Function to update GUI

        # In-memory state
        self.last_swipe_times = {} # {card_id: datetime}
        self.todays_attendance = {} # {card_id: {'in': datetime, 'out': datetime, 'date': date}}
        self.processed_today = set() # {card_id} - To prevent reprocessing 'out' if app restarts mid-day

    def _reset_daily_state_if_needed(self):
        """Checks if the date has changed and resets daily tracking."""
        today = datetime.now().date()
        # Simple reset: Clear if keys exist from a previous date
        keys_to_clear = [
            card_id for card_id, data in self.todays_attendance.items()
            if data.get('date') != today
        ]
        if keys_to_clear:
            logger.info(f"New day ({today}). Resetting daily attendance state for {len(keys_to_clear)} card(s).")
            for card_id in keys_to_clear:
                del self.todays_attendance[card_id]
                if card_id in self.processed_today:
                    self.processed_today.remove(card_id)
            # Also clear last swipe times older than a day? Optional.
            # self.last_swipe_times = {k: v for k, v in self.last_swipe_times.items() if v.date() == today}


    def process_swipe(self, card_id):
        """Main logic to handle a card swipe."""
        self._reset_daily_state_if_needed()
        now = datetime.now()
        today = now.date()
        card_id = str(card_id).strip() # Ensure string format

        logger.info(f"Processing swipe for CARD ID: {card_id} at {now}")

        # 1. Check Swipe Delay
        swipe_delay = self.settings_manager.get_swipe_delay()
        last_swipe = self.last_swipe_times.get(card_id)
        if last_swipe and (now - last_swipe) < swipe_delay:
            logger.warning(f"Swipe rejected for {card_id}: Too soon after last swipe ({now - last_swipe}).")
            self.ui_update_callback(status=f"Quẹt quá nhanh ({card_id})", card_id=card_id)
            return

        self.last_swipe_times[card_id] = now # Update last swipe time immediately

        # 2. Find Employee
        employee_info = self.employee_manager.find_employee_by_card_id(card_id)

        # 3. Handle New Employee
        if not employee_info:
            logger.info(f"Card ID {card_id} not found in database.")
            # Trigger UI to ask for Name/ID
            # This needs to be handled carefully with threading/callbacks
            # For now, we'll just log and update status
            self.ui_update_callback(status=f"Thẻ mới: {card_id}. Cần đăng ký.", card_id=card_id)
            # In a real implementation, the UI would pop up a dialog,
            # get the info, and call employee_manager.add_employee
            # Then potentially re-process this swipe.
            return # Stop processing until registered

        emp_name = employee_info.get('Họ tên', 'N/A')
        emp_id = employee_info.get('ID', 'N/A')
        logger.info(f"Employee found: ID={emp_id}, Name={emp_name}")

        # 4. Get Shift Info
        shift_start_time, shift_end_time = self.settings_manager.get_shift_times()
        allowed_window = self.settings_manager.get_allowed_swipe_window()
        # Calculate the earliest allowed clock-in time
        shift_start_dt_today = datetime.combine(today, shift_start_time)
        earliest_clock_in = shift_start_dt_today - allowed_window

        # 5. Determine Swipe Type (In or Out) and Validate Time
        attendance_record = self.todays_attendance.get(card_id)

        is_clock_in = False
        is_clock_out = False

        if not attendance_record or not attendance_record.get('in'):
            # Potentially a CLOCK IN
            # Rule: "Chỉ chấp nhận quẹt trong khoảng 15 phút trước giờ vào"
            # Interpretation: First swipe (clock-in) must be from 15 mins before shift start onwards.
            # Let's allow clock-in anytime from earliest_clock_in up to shift end? Or maybe a grace period after?
            # Sticking to the strict rule for now: only allow if now >= earliest_clock_in
            # Let's refine: Allow clock-in from earliest_clock_in until shift_end_time? Makes sense.
            shift_end_dt_today = datetime.combine(today, shift_end_time)
            if now >= earliest_clock_in and now <= shift_end_dt_today:
                 is_clock_in = True
                 logger.info(f"Swipe accepted as CLOCK IN for {emp_id} at {now.strftime('%H:%M:%S')}")
            elif now < earliest_clock_in:
                 logger.warning(f"Clock IN rejected for {emp_id}: Too early ({now.strftime('%H:%M:%S')} < {earliest_clock_in.strftime('%H:%M:%S')})")
                 self.ui_update_callback(status=f"Chưa đến giờ vào ca ({emp_name})", card_id=card_id, name=emp_name, emp_id=emp_id)
                 return
            else: # now > shift_end_dt_today
                 # Could this be a late clock-in or a clock-out attempt without prior clock-in?
                 # For simplicity, reject if it's the first swipe and it's after shift end.
                 logger.warning(f"Clock IN rejected for {emp_id}: Swipe after shift end ({now.strftime('%H:%M:%S')} > {shift_end_dt_today.strftime('%H:%M:%S')})")
                 self.ui_update_callback(status=f"Đã qua giờ làm (chưa quẹt vào?) ({emp_name})", card_id=card_id, name=emp_name, emp_id=emp_id)
                 return

        elif attendance_record.get('in') and not attendance_record.get('out'):
            # Potentially a CLOCK OUT
            # Must be after the clock-in time
            if now > attendance_record['in']:
                is_clock_out = True
                logger.info(f"Swipe accepted as CLOCK OUT for {emp_id} at {now.strftime('%H:%M:%S')}")
            else:
                # This shouldn't happen if swipe delay works, but good to check
                logger.warning(f"Clock OUT rejected for {emp_id}: Swipe time ({now}) is not after clock in time ({attendance_record['in']})")
                self.ui_update_callback(status=f"Lỗi thời gian quẹt ra ({emp_name})", card_id=card_id, name=emp_name, emp_id=emp_id)
                return
        else:
            # Already clocked in and out today
            logger.info(f"Employee {emp_id} already clocked in and out today. Ignoring swipe.")
            self.ui_update_callback(status=f"Đã chấm công đủ hôm nay ({emp_name})", card_id=card_id, name=emp_name, emp_id=emp_id)
            return

        # 6. Record Attendance and Log
        time_str = now.strftime('%H:%M:%S')

        if is_clock_in:
            if card_id not in self.todays_attendance:
                self.todays_attendance[card_id] = {'date': today}
            self.todays_attendance[card_id]['in'] = now
            # Log "Giờ Vào"
            success = self.ot_log_manager.write_log_entry(employee_info, now, "Giờ Vào", time_str)
            if success:
                self.ui_update_callback(status=f"Đã vào: {emp_name}", card_id=card_id, name=emp_name, emp_id=emp_id, time=now)
            else:
                 self.ui_update_callback(status=f"LỖI GHI LOG Giờ Vào ({emp_name})", card_id=card_id, name=emp_name, emp_id=emp_id, time=now)


        elif is_clock_out:
            self.todays_attendance[card_id]['out'] = now
            # Log "Giờ Ra"
            success = self.ot_log_manager.write_log_entry(employee_info, now, "Giờ Ra", time_str)
            if success:
                self.ui_update_callback(status=f"Đã ra: {emp_name}", card_id=card_id, name=emp_name, emp_id=emp_id, time=now)
            else:
                 self.ui_update_callback(status=f"LỖI GHI LOG Giờ Ra ({emp_name})", card_id=card_id, name=emp_name, emp_id=emp_id, time=now)
                 # Should we proceed with OT calculation if logging failed? Maybe not.
                 return

            # Calculate Duration and OT only after successful clock-out log
            self._calculate_and_log_ot(card_id, employee_info, now)


    def _calculate_and_log_ot(self, card_id, employee_info, clock_out_time):
        """Calculates work duration, OT, checks limits, and logs total time (as OT hours).""" # Updated docstring
        if card_id not in self.todays_attendance or not self.todays_attendance[card_id].get('in'):
            logger.error(f"Cannot calculate OT for {card_id}: Missing clock-in time.")
            return

        clock_in_time = self.todays_attendance[card_id]['in']
        emp_id = str(employee_info['ID'])
        emp_name = employee_info['Họ tên']
        today = clock_out_time.date()

        # 1. Calculate Actual Work Duration (Effective)
        shift_start_time, shift_end_time = self.settings_manager.get_shift_times()
        shift_start_dt = datetime.combine(today, shift_start_time)
        shift_end_dt = datetime.combine(today, shift_end_time)
        effective_start_time = max(clock_in_time, shift_start_dt)
        effective_end_time = clock_out_time

        if effective_end_time <= effective_start_time:
             work_duration = timedelta(0)
        else:
             work_duration = effective_end_time - effective_start_time

        # 2. Calculate Standard Shift Duration
        if shift_end_time <= shift_start_time: # Handle overnight shifts if ever needed
            standard_shift_duration = timedelta(hours=24) - (datetime.combine(today, shift_start_time) - datetime.combine(today, shift_end_time))
        else:
            standard_shift_duration = datetime.combine(today, shift_end_time) - datetime.combine(today, shift_start_time)

        # 3. Calculate OT
        ot_duration = work_duration - standard_shift_duration
        if ot_duration < timedelta(0):
            ot_duration = timedelta(0)

        # Keep calculation in minutes for limit checking
        ot_minutes_today = round(ot_duration.total_seconds() / 60)
        # total_work_minutes_today = round(work_duration.total_seconds() / 60) # Not currently used for logging

        logger.info(f"Emp ID {emp_id}: Work Duration={work_duration}, Standard Shift={standard_shift_duration}, OT Duration={ot_duration} ({ot_minutes_today} mins)")

        # 4. Check Monthly OT Limit (still uses minutes internally)
        current_monthly_ot_minutes = self.ot_log_manager.get_monthly_ot_minutes(emp_id, today) # This method MUST return minutes
        monthly_limit_minutes = config.MONTHLY_OT_LIMIT_MINUTES

        ot_minutes_to_log = 0 # How many minutes of OT are allowed to be logged for today
        final_status = f"Đã ra: {emp_name}"

        if current_monthly_ot_minutes >= monthly_limit_minutes:
            logger.warning(f"Emp ID {emp_id} has reached monthly OT limit ({current_monthly_ot_minutes}/{monthly_limit_minutes} mins). No further OT will be logged this month.")
            ot_minutes_to_log = 0
            final_status = f"Đã ra: {emp_name} (OT ĐỦ THÁNG)"
            # self.ui_update_callback(...) # Callback happens after logging attempt

        elif current_monthly_ot_minutes + ot_minutes_today > monthly_limit_minutes:
            ot_minutes_to_log = monthly_limit_minutes - current_monthly_ot_minutes
            logger.warning(f"Emp ID {emp_id} will exceed monthly OT limit. Logging partial OT: {ot_minutes_to_log} mins (Today: {ot_minutes_today}, Current: {current_monthly_ot_minutes}, Limit: {monthly_limit_minutes})")
            final_status = f"Đã ra: {emp_name} (GẦN ĐẠT MỨC OT)"
            # self.ui_update_callback(...)

        else:
            ot_minutes_to_log = ot_minutes_today # Log full OT for the day

        # --- CHANGE HERE: Convert allowed OT minutes to hours for logging ---
        # Calculate hours, round to 2 decimal places for cleaner logs
        ot_hours_to_log = round(ot_minutes_to_log / 60.0, 2)
        # --- END CHANGE ---

        # 5. Log "Tổng thời gian" (as OT hours for the day)
        success = self.ot_log_manager.write_log_entry(
            employee_info,
            clock_out_time,
            "Tổng thời gian",
            ot_hours_to_log # Pass hours to log
        )

        if not success:
             logger.error(f"Failed to log 'Tổng thời gian' for Emp ID {emp_id}")
             # Update UI with error status
             self.ui_update_callback(status=f"LỖI GHI LOG Tổng TG ({emp_name})", card_id=card_id, name=emp_name, emp_id=emp_id, time=clock_out_time)
        else:
             # Log success message with hours
             logger.info(f"Logged 'Tổng thời gian' (OT hours) for Emp ID {emp_id}: {ot_hours_to_log}")
             # Update UI with the final status determined by OT check
             self.ui_update_callback(status=final_status, card_id=card_id, name=emp_name, emp_id=emp_id, time=clock_out_time)

        # Mark as processed for the day
        self.processed_today.add(card_id)