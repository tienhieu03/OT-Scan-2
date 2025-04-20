# hid_handler.py
import pywinusb.hid as hid
import time
import threading
import queue
import logging
from collections import defaultdict

import config # Import config for VID/PID



# Simple mapping for US keyboard layout numerals and Enter
# You might need to expand this based on raw report data if it's not standard keycodes
KEYCODE_MAP = {
    0x1E: '1', 0x1F: '2', 0x20: '3', 0x21: '4', 0x22: '5',
    0x23: '6', 0x24: '7', 0x25: '8', 0x26: '9', 0x27: '0',
    # Add mappings for Shift key if needed for special characters on some readers
    0x28: 'ENTER', # Enter key
    # Add other keys if the reader sends them (e.g., numpad keys)
    0x58: 'ENTER', # Numpad Enter might have a different code
    0x59: '1', 0x5A: '2', 0x5B: '3', 0x5C: '4', 0x5D: '5', # Numpad numbers
    0x5E: '6', 0x5F: '7', 0x60: '8', 0x61: '9', 0x62: '0', # Numpad numbers
}
logger = logging.getLogger(__name__)

# --- define HID Usage constants for Keyboard ---
HID_USAGE_PAGE_GENERIC_DESKTOP = 0x01
HID_USAGE_ID_KEYBOARD = 0x06

# --- Important ---
# How raw data is structured depends heavily on the HID device's report descriptor.
# This handler assumes a standard keyboard-like report where:
# - byte 0: Modifier keys (Shift, Ctrl, Alt, GUI) - We ignore this for simple numbers
# - byte 1: Reserved (usually 0)
# - byte 2-7: Keycodes of currently pressed keys (up to 6 keys simultaneously)
# A 'key press' event sends the keycode. A 'key release' event sends all zeros.
# We need to capture the keycode when it appears and ignore the release event.

class HidHandler:
    # --- Modified __init__ ---
    def __init__(self, output_queue, target_vid, target_pid):
        """Initializes the handler with specific VID and PID."""
        self.output_queue = output_queue
        self.target_vid = target_vid # Use passed VID
        self.target_pid = target_pid # Use passed PID
        self.device_buffers = defaultdict(str)
        self.device_last_key_data = defaultdict(lambda: [0]*8)
        self.running = False
        self.thread = None
        self.devices = []
        logger.info(f"HidHandler initialized for VID=0x{self.target_vid:04X}, PID=0x{self.target_pid:04X}")

    def _raw_data_handler(self, data, device_path):
        """Callback function for pywinusb."""
        logger.debug(f"Raw data from {device_path}: {data}")

        # Check if it's a key release event (typically all zeros after byte 1 or 2)
        # Check bytes 2 onwards for keycodes
        is_key_release = all(k == 0 for k in data[2:])
        current_key_data = data[:] # Make a copy

        # Ignore exact same report as last time (key held down) and release events
        if current_key_data == self.device_last_key_data[device_path] or is_key_release:
             if is_key_release:
                 # Clear last key data on release to detect next press correctly
                 self.device_last_key_data[device_path] = [0]*len(data)
             return # Ignore release or key held down

        # Process newly pressed keys (find non-zero keycode in data[2:])
        processed_char = None
        for key_code in data[2:]:
            if key_code != 0: # Found a pressed key
                char = KEYCODE_MAP.get(key_code)
                if char:
                    processed_char = char
                    logger.debug(f"Device {device_path}: Keycode {key_code:02X} -> Char '{char}'")
                    break # Process only the first detected key per report for simplicity

        # Update last key data only if it wasn't a release
        self.device_last_key_data[device_path] = current_key_data

        if processed_char:
            if processed_char == 'ENTER':
                card_id = self.device_buffers[device_path]
                if card_id: # Only process if buffer is not empty
                    logger.info(f"Card ID detected from {device_path}: {card_id}")
                    self.output_queue.put(card_id) # Send complete ID to main thread
                self.device_buffers[device_path] = "" # Clear buffer for this device
            else:
                # Append character to the specific device's buffer
                self.device_buffers[device_path] += processed_char
                # Optional: Add timeout to clear buffer if ENTER isn't received soon

    def _find_devices(self):
        """Find devices based on self.target_vid and self.target_pid."""

        target_interface_str = "&mi_00"

        try:
            device_filter = hid.HidDeviceFilter(vendor_id = self.target_vid,product_id = self.target_pid,usage_page = HID_USAGE_PAGE_GENERIC_DESKTOP,
            usage_id = HID_USAGE_ID_KEYBOARD)
            hid_filtered_devices = device_filter.get_devices()
        except Exception as filter_e:
            logger.error(f"Error creatig or applying HID device filter: {filter_e}",exc_info = True)
            hid_filtered_devices = []

        self.devices = []
        found_paths = set()

        if not hid_filtered_devices:
            logger.warning("No HID devices found matching VID = 0x{self.target_vid:04X},PID = 0x{self.target_pid:04X} AND Usage = Keyboard(0x{HID_USAGE_PAGE_GENERIC_DESKTOP:02X}/0x{HID_USAGE_ID_KEYBOARD:02X}.")
            return False

        logger.info(f"Found {len(hid_filtered_devices)} devices matching VID/PID/Usage. Now filtering for interface '{target_interface_str}'...")
        for device in hid_filtered_devices:
            try:
                device_path = device.device_path

                if target_interface_str in device_path:
                    logger.info(f"Found matching Keyboard interface:'{target_interface_str}':'{device.product_name}' at {device.device_path}") 
                if device_path not in found_paths:
                    self.devices.append(device)
                    found_paths.add(device.device_path)
                    logger.debug(f"Added device path: {device_path}")
                else:
                    logger.debug(f"Skipping device path does not contain '{target_interface_str}': {device_path}")
                    if device.is_plugged() and hasattr(device, 'close'):
                        try:
                            pass
                        except Exception as close_e:
                            logger.warning(f"Could not close non-selected device {device_path}: {close_e}")
            except Exception as e:
                logger.error(f"Error processing filtered device {getattr(device, 'device_path', 'N/A')}: {e}")
                if device and hasattr(device, 'is_plugged') and hasattr(device, 'close'): # Check if closable
                    try:
                        device.close()
                    except Exception as close_e:
                         logger.error(f"Error closing device {device.device_path} after error: {close_e}")


        if not self.devices:
            logger.warning(f"Could not find any device matching VID/PID/Usage AND containing '{target_interface_str}' in its path")
            logger.warning(f"Please verify the device path in Device Manager and the '{target_interface_str}' string.")
            return False

        logger.info(f"Found {len(self.devices)} device interface(s) matching all criteria (including '{target_interface_str}').")
        return True


    def _run(self):
        """Worker thread function."""
        while self.running:
            devices_connected = self.devices and all(d.is_plugged() for d in self.devices)

            if not devices_connected:
                logger.info("Attempting to find/reconnect ZKTeco devices...")
                for dev in self.devices:
                    if dev.is_opened():
                        logger.info(f"Closing previously opened device: {dev.device_path}")
                        dev.close()
                self.devices = []
                self.device_buffers.clear()
                self.device_last_key_data.clear()
                if self._find_devices():
                    try:
                        all_opened = True
                        for device in self.devices:
                            if not device.is_opened():
                                logger.info(f"Opening device: {device.device_path}")
                                device.open()
                                logger.info(f"Setting raw data handler for: {device.device_path}")
                                device.set_raw_data_handler(lambda data, dp=device.device_path: self._raw_data_handler(data, dp))
                                logger.info(f"Handler set successfully for:{ device.device_path}")
                            else:
                                logger.warning(f"Device already open? {device.device_path}")
                    except Exception as e:
                        logger.error(f"Error opening device for setting handler: {e}",exc_info=True)
                        for dev in self.devices:
                            if dev.is_opened():
                                dev.close()
                        self.devices = [] # Reset devices list
                        time.sleep(5) # Wait before retrying
                        continue # Skip to next loop iteration
                else:
                    # No devices found, wait longer before retrying
                    time.sleep(10)
                    continue # Skip to next loop iteration

            # Keep thread alive while devices are connected and handlers are set
            # pywinusb handles callbacks in its own internal mechanism when device is open
            time.sleep(1) # Check connection status periodically
        # Cleanup when stopping
        logger.info("HID handler stopping. Closing devices.")
        for device in self.devices:
            if device.is_opened():
                device.close()
        logger.info("HID handler stopped.")

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            logger.info("HID handler thread started.")
        else:
            logger.warning("HID handler already running.")

    def stop(self):
        if self.running:
            logger.info("Stopping HID handler thread...")
            self.running = False
            if self.thread:
                self.thread.join(timeout=2) # Wait for thread to finish
                if self.thread.is_alive():
                     logger.warning("HID handler thread did not stop gracefully.")
        else:
            logger.info("HID handler already stopped.")