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

    def manage_window_state(self, minimize: bool = True) -> bool:
        """Manage YouTube Music window state."""
        try:
            if minimize:
                self.controller.device.shell('input keyevent KEYCODE_HOME')
                time.sleep(0.5)
                self.controller.device.shell('input keyevent KEYCODE_HOME')
                logger.info("Minimized YouTube Music window")
            else:
                self.controller.device.shell('input keyevent KEYCODE_APP_SWITCH')
                time.sleep(1)
                ytm_app = self.controller.device(text="YouTube Music")
                if ytm_app.exists:
                    ytm_app.click()
                else:
                    self.controller.device.app_stop(self.controller.package_name)
                    time.sleep(1)
                    self.controller.device.app_start(self.controller.package_name)
                time.sleep(2)
                logger.info("Restored YouTube Music window")
            return True
        except Exception as e:
            logger.error(f"Error managing window state: {e}")
            return False

    def get_isoclipboard_delay(self) -> int:
        """Get random delay between 22-30 minutes in seconds for IsoClipboard."""
        minutes = random.randint(2, 5)
        seconds = minutes * 60
        next_time = time.strftime('%H:%M:%S', time.localtime(time.time() + seconds))
        logger.info(f"Next IsoClipboard action scheduled in {minutes} minutes (at {next_time})")
        return seconds

    def get_music_control_delay(self) -> int:
        """Get random delay between 45 seconds and 6 minutes for music controls."""
        seconds = random.randint(45, 6 * 60)
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        next_time = time.strftime('%H:%M:%S', time.localtime(time.time() + seconds))
        if minutes > 0:
            logger.info(f"Next music control action in {minutes}m {remaining_seconds}s (at {next_time})")
        else:
            logger.info(f"Next music control action in {seconds}s (at {next_time})")
        return seconds

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

            self.manage_window_state(minimize=True)
            time.sleep(1)

            self.last_isoclipboard_time = time.time()
            self.get_isoclipboard_delay()
            logger.info("Initial automation setup complete, starting regular intervals")
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
                isoclipboard_delay = self.get_isoclipboard_delay()

                if time_since_isoclipboard >= isoclipboard_delay:
                    self.manage_window_state(minimize=True)
                    time.sleep(1)
                    logger.info("Performing IsoClipboard handling")
                    self.manage_window_state(minimize=False)
                    time.sleep(3)
                    if self.controller.handle_isoclipboard():
                        logger.info("Successfully performed IsoClipboard handling")
                        self.last_isoclipboard_time = current_time
                    else:
                        logger.error("Failed to perform IsoClipboard handling")
                        self.last_isoclipboard_time = current_time - (isoclipboard_delay - 300)
                    self.manage_window_state(minimize=True)
                    time.sleep(1)

                # Perform random music control action
                music_delay = self.get_music_control_delay()
                time.sleep(music_delay)

                self.manage_window_state(minimize=False)
                time.sleep(3)

                if not self.controller.device(packageName=self.controller.package_name).exists:
                    logger.warning("App not in foreground, retrying restore")
                    self.manage_window_state(minimize=False)
                    time.sleep(3)

                action, action_name = self.get_random_music_action()
                logger.info(f"Performing action: {action_name}")

                if self.controller.device(packageName=self.controller.package_name).exists:
                    if action():
                        logger.info(f"Successfully performed {action_name}")
                    else:
                        logger.error(f"Failed to perform {action_name}")
                else:
                    logger.error("App not properly restored before action")

                self.manage_window_state(minimize=True)
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error in automation: {e}")
                self.manage_window_state(minimize=True)
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

        self.manage_window_state(minimize=True)
        time.sleep(1)

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