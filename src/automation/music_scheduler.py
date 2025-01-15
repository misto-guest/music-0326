# src/automation/music_scheduler.py

import random
import threading
import time
from typing import Optional, Tuple, Callable
from src.utils.logging_utils import setup_logger
from src.controllers.app_controllers.youtube_music import YouTubeMusicController

logger = setup_logger(__name__)


class MusicAutomation:
    def __init__(self, controller: YouTubeMusicController):
        self.controller = controller
        self.running = False
        self.automation_thread: Optional[threading.Thread] = None
        self.last_isoclipboard_time = 0

    def get_isoclipboard_delay(self) -> int:
        """Get random delay between 22-30 minutes in seconds for IsoClipboard."""
        return random.randint(22 * 60, 30 * 60)

    def get_music_control_delay(self) -> int:
        """Get random delay between 45 seconds and 6 minutes for music controls."""
        return random.randint(45, 6 * 60)

    def get_random_music_action(self) -> tuple[Callable, str]:
        """Get random music control action to perform."""
        actions = [
            (self.controller.next_track, "Next track"),
            (self.controller.like_current_song, "Like song"),
            (self.controller.previous_track, "Previous track")
        ]
        return random.choice(actions)

    def perform_initial_setup(self) -> bool:
        """Perform initial setup before starting automation."""
        try:
            logger.info("Starting initial setup...")
            if not self.controller.start_initial_automation():
                logger.error("Failed to complete initial setup")
                return False
            logger.info("Initial setup completed successfully")
            self.last_isoclipboard_time = time.time()
            return True
        except Exception as e:
            logger.error(f"Error in initial setup: {e}")
            return False

    def perform_random_automation(self):
        """Perform random automation actions with different timing patterns."""
        while self.running:
            try:
                current_time = time.time()
                time_since_isoclipboard = current_time - self.last_isoclipboard_time

                # Check if it's time for IsoClipboard action
                if time_since_isoclipboard >= self.get_isoclipboard_delay():
                    logger.info("Performing IsoClipboard handling")
                    if self.controller.handle_isoclipboard():
                        logger.info("Successfully performed IsoClipboard handling")
                        self.last_isoclipboard_time = current_time
                    else:
                        logger.error("Failed to perform IsoClipboard handling")

                # Perform random music control action
                music_delay = self.get_music_control_delay()
                logger.info(f"Waiting {music_delay} seconds before next music control action")
                time.sleep(music_delay)

                action, action_name = self.get_random_music_action()
                logger.info(f"Performing action: {action_name}")

                if action():
                    logger.info(f"Successfully performed {action_name}")
                else:
                    logger.error(f"Failed to perform {action_name}")

            except Exception as e:
                logger.error(f"Error in automation: {e}")
                time.sleep(60)

    def start_automation(self):
        """Start the automation process."""
        if self.running:
            logger.warning("Automation already running")
            return

        # Perform initial setup
        if not self.perform_initial_setup():
            logger.error("Failed to complete initial setup, not starting automation")
            return

        self.running = True
        self.automation_thread = threading.Thread(target=self.perform_random_automation)
        self.automation_thread.daemon = True
        self.automation_thread.start()
        logger.info("Started music automation")

    def stop_automation(self):
        """Stop the automation process."""
        if not self.running:
            logger.warning("Automation not running")
            return

        self.running = False
        if self.automation_thread:
            self.automation_thread.join()

        # Cleanup: ensure YouTube Music is closed
        if not self.controller.close_youtube_music():
            logger.warning("Failed to close YouTube Music during cleanup")

        logger.info("Stopped music automation")