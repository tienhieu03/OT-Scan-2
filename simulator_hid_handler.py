# simulator_hid_handler.py
import threading
import time
import random
import queue # Although not used directly here, good practice if extending
import logging

logger = logging.getLogger(__name__)

# --- List of Card IDs to Simulate ---
# Add IDs that ARE in your employee_database.xlsx (if you have one)
# Add IDs that ARE NOT in your database to test the registration flow
SIMULATED_CARD_IDS = [
    "1002003001", # Example known ID
    "1002003002", # Example known ID
    "9998887771", # Example UNKNOWN ID
    "1112223334", # Example UNKNOWN ID
    "1002003003", # Example known ID
    "ABCDEF1234", # Example non-numeric ID (if your reader could produce this)
]

class SimulatorHidHandler:
    def __init__(self, output_queue):
        """Mimics the HidHandler interface."""
        self.output_queue = output_queue
        self.running = False
        self.thread = None
        logger.info("Initialized SimulatorHidHandler")

    def _run(self):
        """Worker thread function to simulate swipes."""
        logger.info("Simulator thread started.")
        while self.running:
            try:
                # Wait for a random time (e.g., 3 to 10 seconds)
                sleep_time = random.uniform(3.0, 10.0)
                time.sleep(sleep_time)

                if not self.running: # Check again after sleep
                    break

                # Choose a random card ID from the list
                card_id_to_send = random.choice(SIMULATED_CARD_IDS)

                # Put the simulated card ID into the queue
                self.output_queue.put(card_id_to_send)
                logger.info(f"[SIMULATOR] Sent Card ID: {card_id_to_send}")

            except Exception as e:
                logger.error(f"Error in simulator thread: {e}")
                # Avoid crashing the simulator thread on unexpected errors
                time.sleep(5) # Wait a bit before retrying

        logger.info("Simulator thread finished.")

    def start(self):
        """Starts the simulation thread."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            logger.info("SimulatorHidHandler started.")
        else:
            logger.warning("SimulatorHidHandler already running.")

    def stop(self):
        """Stops the simulation thread."""
        if self.running:
            logger.info("Stopping SimulatorHidHandler thread...")
            self.running = False
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=2) # Wait for thread to finish
                if self.thread.is_alive():
                     logger.warning("Simulator thread did not stop gracefully.")
        else:
            logger.info("SimulatorHidHandler already stopped.")