# src/automation/multi_app_scheduler.py

import random
import threading
import time
from typing import Dict, Optional, List, Tuple, Callable
from src.utils.logging_utils import setup_logger
from src.controllers.app_controllers.youtube_music import YouTubeMusicController
from src.controllers.app_controllers.apple_music import AppleMusicController

logger = setup_logger(__name__)


class MultiMusicAutomation:
    """Handles automation for multiple music apps."""

    def __init__(self, youtube_controller: Optional[YouTubeMusicController] = None,
                 apple_controller: Optional[AppleMusicController] = None):
        """Initialize automation with controllers."""
        self.youtube_controller = youtube_controller
        self.apple_controller = apple_controller
        self.running = False
        self.automation_thread: Optional[threading.Thread] = None
        self.last_youtube_action = time.time()
        self.last_apple_action = time.time()
        self.last_youtube_isoclipboard = time.time()
        self.last_apple_isoclipboard = time.time()

    def _youtube_initial_setup(self) -> bool:
        """Initial setup for YouTube Music automation."""
        try:
            logger.info("Starting YouTube Music initial setup...")

            # Make sure YT Music is closed
            if not self.youtube_controller.force_stop():
                logger.error("Failed to close YouTube Music")
                return False
            time.sleep(2)

            # Handle IsoClipboard for YT Music
            if not self.youtube_controller.handle_isoclipboard():
                logger.error("Failed YouTube Music IsoClipboard setup")
                return False

            self.last_youtube_isoclipboard = time.time()
            logger.info("YouTube Music initial setup completed")
            return True

        except Exception as e:
            logger.error(f"Error in YouTube Music initial setup: {e}")
            return False

    def _apple_initial_setup(self) -> bool:
        """Initial setup for Apple Music automation with retry logic."""
        try:
            logger.info("Starting Apple Music initial setup...")

            # Step 1: Make sure Apple Music is closed
            for attempt in range(3):
                if self.apple_controller.force_stop():
                    break
                logger.warning(f"Failed to close Apple Music, attempt {attempt + 1}")
                time.sleep(2)
            time.sleep(2)

            # Step 2: Start IsoClipboard sequence
            logger.info("Starting IsoClipboard sequence")
            iso_attempts = 0
            while iso_attempts < 3:
                if self.apple_controller.handle_isoclipboard():
                    self.last_apple_isoclipboard = time.time()
                    logger.info("Apple Music initial setup completed successfully")
                    return True
                logger.warning(f"Failed IsoClipboard setup, attempt {iso_attempts + 1}")
                time.sleep(2)
                iso_attempts += 1

            logger.error("Failed Apple Music IsoClipboard setup after all retries")
            return False

        except Exception as e:
            logger.error(f"Error in Apple Music initial setup: {e}")
            return False

    def get_isoclipboard_delay(self, is_youtube: bool = True) -> int:
        """Get random delay between actions."""
        if is_youtube:
            minutes = random.randint(22, 33)  # 22-33 minutes for YouTube
        else:
            minutes = random.randint(25, 35)  # 25-35 minutes for Apple Music

        seconds = minutes * 60
        next_time = time.strftime('%H:%M:%S', time.localtime(time.time() + seconds))
        app_name = "YouTube Music" if is_youtube else "Apple Music"
        logger.info(f"Next {app_name} IsoClipboard action in {minutes}m (at {next_time})")
        return seconds

    def get_music_control_delay(self, is_youtube: bool = True) -> int:
        """Get random delay between actions."""
        if is_youtube:
            seconds = random.randint(45, 6 * 60)  # 45s to 6m for YouTube
        else:
            seconds = random.randint(60, 7 * 60)  # 1m to 7m for Apple Music

        minutes = seconds // 60
        remaining_seconds = seconds % 60
        next_time = time.strftime('%H:%M:%S', time.localtime(time.time() + seconds))
        app_name = "YouTube Music" if is_youtube else "Apple Music"

        if minutes > 0:
            logger.info(f"Next {app_name} action in {minutes}m {remaining_seconds}s (at {next_time})")
        else:
            logger.info(f"Next {app_name} action in {seconds}s (at {next_time})")
        return seconds

    def get_youtube_action(self) -> tuple[Callable, str]:
        """Get random YouTube Music action."""
        actions = [
            (self.youtube_controller.next_track, "Next track"),
            (self.youtube_controller.like_current_song, "Like song"),
            (self.youtube_controller.previous_track, "Previous track")
        ]
        return random.choice(actions)

    def get_apple_action(self) -> tuple[Callable, str]:
        """Get random Apple Music action."""
        actions = [
            (self.apple_controller.next_track, "Next track"),
            (self.apple_controller.like_current_song, "Like song"),
            (self.apple_controller.previous_track, "Previous track"),
        ]
        return random.choice(actions)

    def _youtube_automation_loop(self):
        """Handle YouTube Music automation."""
        if not self._youtube_initial_setup():
            logger.error("Failed YouTube Music initial setup, stopping automation")
            self.running = False
            return

        while self.running:
            try:
                current_time = time.time()

                # Handle YouTube Music IsoClipboard
                youtube_iso_elapsed = current_time - self.last_youtube_isoclipboard
                if youtube_iso_elapsed >= self.get_isoclipboard_delay(is_youtube=True):
                    logger.info("Performing YouTube Music IsoClipboard")
                    if self.youtube_controller.handle_isoclipboard():
                        self.last_youtube_isoclipboard = current_time
                        self.last_youtube_action = current_time
                        logger.info("YouTube Music IsoClipboard successful")
                    else:
                        logger.error("YouTube Music IsoClipboard failed")

                # YouTube Music action
                action, action_name = self.get_youtube_action()
                delay = self.get_music_control_delay(is_youtube=True)
                time.sleep(delay)

                logger.info(f"Performing YouTube Music action: {action_name}")
                if action():
                    self.last_youtube_action = time.time()
                    logger.info(f"YouTube Music {action_name} successful")
                else:
                    logger.error(f"YouTube Music {action_name} failed")

            except Exception as e:
                logger.error(f"Error in YouTube Music automation: {e}")
                time.sleep(60)

    def _apple_automation_loop(self):
        """Handle Apple Music automation."""
        while self.running:
            try:
                current_time = time.time()

                # Check internet connection
                if not self.apple_controller.check_internet_connection():
                    logger.error("No internet connection, waiting...")
                    time.sleep(60)
                    continue

                # Handle Apple Music IsoClipboard
                apple_iso_elapsed = current_time - self.last_apple_isoclipboard
                if apple_iso_elapsed >= self.get_isoclipboard_delay(is_youtube=False):
                    logger.info("Performing Apple Music IsoClipboard")

                    # Prepare device for IsoClipboard action
                    if not self.apple_controller.prepare_for_action():
                        logger.error("Failed to prepare for IsoClipboard action")
                        time.sleep(30)
                        continue

                    if self.apple_controller.handle_isoclipboard():
                        self.last_apple_isoclipboard = current_time
                        self.last_apple_action = current_time
                        logger.info("Apple Music IsoClipboard successful")
                    else:
                        logger.error("Apple Music IsoClipboard failed")

                    # Minimize after IsoClipboard
                    self.apple_controller.manage_window_state(minimize=True)

                # Apple Music action
                action, action_name = self.get_apple_action()
                delay = self.get_music_control_delay(is_youtube=False)
                time.sleep(delay)

                # Prepare device for music action
                if not self.apple_controller.prepare_for_action():
                    logger.error(f"Failed to prepare for {action_name}")
                    time.sleep(30)
                    continue

                logger.info(f"Performing Apple Music action: {action_name}")
                if action():
                    self.last_apple_action = time.time()
                    logger.info(f"Apple Music {action_name} successful")
                else:
                    logger.error(f"Apple Music {action_name} failed")

                # Minimize after action
                self.apple_controller.manage_window_state(minimize=True)

            except Exception as e:
                logger.error(f"Error in Apple Music automation: {e}")
                time.sleep(60)

    def start_automation(self):
        """Start both apps automation."""
        if self.running:
            logger.warning("Automation already running")
            return

        if not self.youtube_controller or not self.apple_controller:
            logger.error("Both controllers are required for multi-app automation")
            return

        self.running = True
        self.automation_thread = threading.Thread(target=self._both_automation_loop)
        self.automation_thread.daemon = True
        self.automation_thread.start()
        logger.info("Started multi-app automation")

    def _both_automation_loop(self):
        """Handle automation for both apps."""
        if not self._youtube_initial_setup() or not self._apple_initial_setup():
            logger.error("Failed initial setup, stopping automation")
            self.running = False
            return

        while self.running:
            try:
                current_time = time.time()

                # Alternate between apps based on last action time
                if current_time - self.last_youtube_action > current_time - self.last_apple_action:
                    # YouTube Music turn
                    action, action_name = self.get_youtube_action()
                    delay = self.get_music_control_delay(is_youtube=True)
                    time.sleep(delay)

                    logger.info(f"Performing YouTube Music action: {action_name}")
                    if action():
                        self.last_youtube_action = time.time()
                        logger.info(f"YouTube Music {action_name} successful")
                    else:
                        logger.error(f"YouTube Music {action_name} failed")
                else:
                    # Apple Music turn
                    action, action_name = self.get_apple_action()
                    delay = self.get_music_control_delay(is_youtube=False)
                    time.sleep(delay)

                    logger.info(f"Performing Apple Music action: {action_name}")
                    if action():
                        self.last_apple_action = time.time()
                        logger.info(f"Apple Music {action_name} successful")
                    else:
                        logger.error(f"Apple Music {action_name} failed")

                # Handle IsoClipboard for both apps
                youtube_iso_elapsed = current_time - self.last_youtube_isoclipboard
                if youtube_iso_elapsed >= self.get_isoclipboard_delay(is_youtube=True):
                    if self.youtube_controller.handle_isoclipboard():
                        self.last_youtube_isoclipboard = time.time()

                apple_iso_elapsed = current_time - self.last_apple_isoclipboard
                if apple_iso_elapsed >= self.get_isoclipboard_delay(is_youtube=False):
                    if self.apple_controller.handle_isoclipboard():
                        self.last_apple_isoclipboard = time.time()

            except Exception as e:
                logger.error(f"Error in automation: {e}")
                time.sleep(60)

    def start_youtube_only(self):
        """Start YouTube Music automation only."""
        if self.running:
            logger.warning("Automation already running")
            return
        if not self.youtube_controller:
            logger.error("No YouTube Music controller provided")
            return

        self.running = True
        self.automation_thread = threading.Thread(target=self._youtube_automation_loop)
        self.automation_thread.daemon = True
        self.automation_thread.start()
        logger.info("Started YouTube Music automation")

    def start_apple_only(self):
        """Start Apple Music automation only."""
        if self.running:
            logger.warning("Automation already running")
            return False

        if not self.apple_controller:
            logger.error("No Apple Music controller provided")
            return False

        # Initialize retry counter
        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                # Check internet connection before starting
                if not self.apple_controller.check_internet_connection():
                    logger.error("No internet connection, retrying...")
                    time.sleep(5)
                    retry_count += 1
                    continue

                # Ensure screen is active with retry logic
                screen_active_attempts = 0
                while screen_active_attempts < 3:
                    if self.apple_controller.ensure_screen_active():
                        break
                    logger.warning(f"Screen activation attempt {screen_active_attempts + 1} failed, retrying...")
                    time.sleep(2)
                    screen_active_attempts += 1

                if screen_active_attempts >= 3:
                    logger.error("Failed to ensure screen active after multiple attempts")
                    return False

                # Perform initial setup
                if not self._apple_initial_setup():
                    logger.error("Failed Apple Music initial setup, retrying...")
                    retry_count += 1
                    continue

                # Start automation thread
                self.running = True
                self.automation_thread = threading.Thread(target=self._apple_automation_loop)
                self.automation_thread.daemon = True
                self.automation_thread.start()

                # Minimize after starting
                if not self.apple_controller.manage_window_state(minimize=True):
                    logger.warning("Failed to minimize window but automation is running")

                logger.info("Started Apple Music automation successfully")
                return True

            except Exception as e:
                logger.error(f"Error during automation start (attempt {retry_count + 1}): {e}")
                retry_count += 1
                time.sleep(2)

        logger.error("Failed to start Apple Music automation after all retries")
        return False

    def start_automation(self):
        """Start both apps automation with proper error handling."""
        if self.running:
            logger.warning("Automation already running")
            return False

        if not self.youtube_controller or not self.apple_controller:
            logger.error("Both controllers are required for multi-app automation")
            return False

        # Perform initial setup checks
        if not self._youtube_initial_setup() or not self._apple_initial_setup():
            logger.error("Failed initial setup, not starting automation")
            return False

        self.running = True
        self.automation_thread = threading.Thread(target=self._both_automation_loop)
        self.automation_thread.daemon = True
        self.automation_thread.start()

        logger.info("Started multi-app automation")
        return True