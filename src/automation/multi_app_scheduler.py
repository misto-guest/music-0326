# src/automation/multi_app_scheduler.py

import random
import threading
import time
from typing import Optional, List, Tuple, Callable
from src.utils.logging_utils import setup_logger
from src.controllers.app_controllers.youtube_music import YouTubeMusicController
from src.controllers.app_controllers.apple_music import AppleMusicController
from src.controllers.app_controllers.amazon_music import AmazonMusicController
from src.controllers.mutex_mixin import MutexMixin, with_device_lock

logger = setup_logger(__name__)


class MultiMusicAutomation(MutexMixin):
    """Handles automation for multiple music apps with device-wide mutex control."""

    def __init__(self):
        """Initialize automation with controllers."""
        super().__init__()  # Initialize MutexMixin internals
        self.youtube_controller = None
        self.apple_controller = None
        self.amazon_controller = None
        self.running = False
        self.automation_thread: Optional[threading.Thread] = None

        # Last action timestamps
        self.last_youtube_action = 0
        self.last_apple_action = 0
        self.last_amazon_action = 0
        self.last_youtube_isoclipboard = 0
        self.last_apple_isoclipboard = 0
        self.last_amazon_isoclipboard = 0

    def add_controller(self, app_type: str, controller) -> None:
        """Add a controller for specific app type."""
        if app_type == "youtube_music":
            self.youtube_controller = controller
        elif app_type == "apple_music":
            self.apple_controller = controller
        elif app_type == "amazon_music":
            self.amazon_controller = controller

    @with_device_lock
    def _run_device_locked(self, func: Callable, *args, **kwargs):
        """All UI-interacting calls go here to ensure thread safety."""
        return func(*args, **kwargs)

    def _youtube_initial_setup(self) -> bool:
        try:
            logger.info("Starting YouTube Music initial setup...")
            if not self._run_device_locked(self.youtube_controller.force_stop):
                logger.error("Failed to close YouTube Music")
                return False
            time.sleep(2)
            if not self._run_device_locked(self.youtube_controller.handle_isoclipboard):
                logger.error("Failed YouTube Music IsoClipboard setup")
                return False
            self.last_youtube_isoclipboard = time.time()
            # Minimize window
            if not self._run_device_locked(self.youtube_controller.manage_window_state, minimize=True):
                logger.warning("Failed to minimize YouTube Music window")
            logger.info("YouTube Music initial setup completed")
            return True
        except Exception as e:
            logger.error(f"Error in YouTube Music initial setup: {e}")
            return False

    def _apple_initial_setup(self) -> bool:
        try:
            logger.info("Starting Apple Music initial setup...")
            if not self._run_device_locked(self.apple_controller.force_stop):
                logger.warning("Failed to close Apple Music")
            time.sleep(2)
            if not self._run_device_locked(self.apple_controller.handle_isoclipboard):
                logger.error("Failed Apple Music IsoClipboard setup")
                return False
            self.last_apple_isoclipboard = time.time()
            if not self._run_device_locked(self.apple_controller.manage_window_state, minimize=True):
                logger.warning("Failed to minimize Apple Music window")
            logger.info("Apple Music initial setup completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error in Apple Music initial setup: {e}")
            return False

    def _amazon_initial_setup(self) -> bool:
        try:
            logger.info("Starting Amazon Music initial setup...")
            if not self._run_device_locked(self.amazon_controller.force_stop):
                logger.warning("Failed to close Amazon Music")
            time.sleep(2)
            if not self._run_device_locked(self.amazon_controller.handle_isoclipboard):
                logger.error("Failed Amazon Music IsoClipboard setup")
                return False
            self.last_amazon_isoclipboard = time.time()
            if not self._run_device_locked(self.amazon_controller.manage_window_state, minimize=True):
                logger.warning("Failed to minimize Amazon Music window")
            logger.info("Amazon Music initial setup completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error in Amazon Music initial setup: {e}")
            return False

    def get_isoclipboard_delay(self, app_type: str) -> int:
        """Get random delay between iso-clipboard actions."""
        if app_type == "youtube_music":
            minutes = random.randint(22, 33)  # 22-33 minutes for YouTube
        elif app_type == "apple_music":
            minutes = random.randint(25, 35)  # 25-35 minutes for Apple Music
        else:  # amazon_music
            minutes = random.randint(27, 37)  # 27-37 minutes for Amazon Music

        seconds = minutes * 60
        next_time = time.strftime('%H:%M:%S', time.localtime(time.time() + seconds))
        app_name = {"youtube_music": "YouTube Music",
                    "apple_music": "Apple Music",
                    "amazon_music": "Amazon Music"}[app_type]
        logger.info(f"Next {app_name} IsoClipboard action in {minutes}m (at {next_time})")
        return seconds

    def get_music_control_delay(self, app_type: str) -> int:
        """Get random delay for music-control actions."""
        if app_type == "youtube_music":
            seconds = random.randint(45, 6 * 60)  # 45s to 6m for YouTube
        elif app_type == "apple_music":
            seconds = random.randint(60, 7 * 60)  # 1m to 7m for Apple Music
        else:  # amazon_music
            seconds = random.randint(50, 5 * 60)  # 50s to 5m for Amazon Music

        minutes = seconds // 60
        remaining_seconds = seconds % 60
        next_time = time.strftime('%H:%M:%S', time.localtime(time.time() + seconds))

        app_name = {"youtube_music": "YouTube Music",
                    "apple_music": "Apple Music",
                    "amazon_music": "Amazon Music"}[app_type]
        if minutes > 0:
            logger.info(f"Next {app_name} action in {minutes}m {remaining_seconds}s (at {next_time})")
        else:
            logger.info(f"Next {app_name} action in {seconds}s (at {next_time})")
        return seconds

    def get_youtube_action(self) -> Tuple[Callable, str]:
        """Get random YouTube Music action."""
        actions = [
            (self.youtube_controller.next_track, "Next track"),
            (self.youtube_controller.like_current_song, "Like song"),
            (self.youtube_controller.previous_track, "Previous track")
        ]
        return random.choice(actions)

    def get_apple_action(self) -> Tuple[Callable, str]:
        """Get random Apple Music action."""
        actions = [
            (self.apple_controller.next_track, "Next track"),
            (self.apple_controller.like_current_song, "Like song"),
            (self.apple_controller.previous_track, "Previous track")
        ]
        return random.choice(actions)

    def get_amazon_action(self) -> Tuple[Callable, str]:
        """Get random Amazon Music action."""
        actions = [
            (self.amazon_controller.next_track, "Next track"),
            (self.amazon_controller.like_current_song, "Like song"),
            (self.amazon_controller.previous_track, "Previous track")
        ]
        return random.choice(actions)

    def _automation_loop(self):
        """Handle automation for all music apps."""
        while self.running:
            try:
                current_time = time.time()

                # Handle YouTube Music
                if self.youtube_controller:
                    youtube_iso_elapsed = current_time - self.last_youtube_isoclipboard
                    if youtube_iso_elapsed >= self.get_isoclipboard_delay("youtube_music"):
                        logger.info("Performing YouTube Music IsoClipboard")
                        if self._run_device_locked(self.youtube_controller.handle_isoclipboard):
                            self.last_youtube_isoclipboard = time.time()
                            self.last_youtube_action = time.time()
                            self._run_device_locked(self.youtube_controller.device.press, "home")
                            logger.info("YouTube Music IsoClipboard successful")

                # Handle Apple Music
                if self.apple_controller:
                    apple_iso_elapsed = current_time - self.last_apple_isoclipboard
                    if apple_iso_elapsed >= self.get_isoclipboard_delay("apple_music"):
                        logger.info("Performing Apple Music IsoClipboard")
                        if self._run_device_locked(self.apple_controller.handle_isoclipboard):
                            self.last_apple_isoclipboard = time.time()
                            self.last_apple_action = time.time()
                            self._run_device_locked(self.apple_controller.device.press, "home")
                            logger.info("Apple Music IsoClipboard successful")

                # Handle Amazon Music
                if self.amazon_controller:
                    amazon_iso_elapsed = current_time - self.last_amazon_isoclipboard
                    if amazon_iso_elapsed >= self.get_isoclipboard_delay("amazon_music"):
                        logger.info("Performing Amazon Music IsoClipboard")
                        if self._run_device_locked(self.amazon_controller.handle_isoclipboard):
                            self.last_amazon_isoclipboard = time.time()
                            self.last_amazon_action = time.time()
                            self._run_device_locked(self.amazon_controller.device.press, "home")
                            logger.info("Amazon Music IsoClipboard successful")

                # Determine which app's turn it is based on last action time
                youtube_elapsed = current_time - self.last_youtube_action if self.youtube_controller else float('inf')
                apple_elapsed = current_time - self.last_apple_action if self.apple_controller else float('inf')
                amazon_elapsed = current_time - self.last_amazon_action if self.amazon_controller else float('inf')

                # Choose app with longest elapsed time
                elapsed_times = {
                    'youtube': youtube_elapsed if self.youtube_controller else float('inf'),
                    'apple': apple_elapsed if self.apple_controller else float('inf'),
                    'amazon': amazon_elapsed if self.amazon_controller else float('inf')
                }
                chosen_app = max(elapsed_times.items(), key=lambda x: x[1])[0]

                # Execute action for chosen app
                if chosen_app == 'youtube' and self.youtube_controller:
                    action, action_name = self.get_youtube_action()
                    delay = self.get_music_control_delay("youtube_music")
                    time.sleep(delay)
                    if self._run_device_locked(self.youtube_controller.prepare_for_action):
                        if self._run_device_locked(action):
                            self.last_youtube_action = time.time()
                            self._run_device_locked(self.youtube_controller.device.press, "home")
                            logger.info(f"YouTube Music {action_name} successful")

                elif chosen_app == 'apple' and self.apple_controller:
                    action, action_name = self.get_apple_action()
                    delay = self.get_music_control_delay("apple_music")
                    time.sleep(delay)
                    if self._run_device_locked(self.apple_controller.prepare_for_action):
                        if self._run_device_locked(action):
                            self.last_apple_action = time.time()
                            self._run_device_locked(self.apple_controller.device.press, "home")
                            logger.info(f"Apple Music {action_name} successful")

                elif chosen_app == 'amazon' and self.amazon_controller:
                    action, action_name = self.get_amazon_action()
                    delay = self.get_music_control_delay("amazon_music")
                    time.sleep(delay)
                    if self._run_device_locked(self.amazon_controller.prepare_for_action):
                        if self._run_device_locked(action):
                            self.last_amazon_action = time.time()
                            self._run_device_locked(self.amazon_controller.device.press, "home")
                            logger.info(f"Amazon Music {action_name} successful")

            except Exception as e:
                logger.error(f"Error in automation loop: {e}")
                time.sleep(60)

    def start_automation(self):
        """Start automation for all configured apps."""
        if self.running:
            logger.warning("Automation already running")
            return False

        # Check if at least one controller is available
        if not any([self.youtube_controller, self.apple_controller, self.amazon_controller]):
            logger.error("No music controllers available")
            return False

        # Perform initial setup for each configured app
        if self.youtube_controller and not self._youtube_initial_setup():
            logger.error("Failed YouTube Music initial setup")
            return False

        if self.apple_controller and not self._apple_initial_setup():
            logger.error("Failed Apple Music initial setup")
            return False

        if self.amazon_controller and not self._amazon_initial_setup():
            logger.error("Failed Amazon Music initial setup")
            return False

        # Initialize all timers
        current_time = time.time()
        self.last_youtube_action = current_time
        self.last_apple_action = current_time
        self.last_amazon_action = current_time
        self.last_youtube_isoclipboard = current_time
        self.last_apple_isoclipboard = current_time
        self.last_amazon_isoclipboard = current_time

        # Log initial delays
        if self.youtube_controller:
            self.get_isoclipboard_delay("youtube_music")
            self.get_music_control_delay("youtube_music")
        if self.apple_controller:
            self.get_isoclipboard_delay("apple_music")
            self.get_music_control_delay("apple_music")
        if self.amazon_controller:
            self.get_isoclipboard_delay("amazon_music")
            self.get_music_control_delay("amazon_music")

        # Start automation
        self.running = True
        self.automation_thread = threading.Thread(target=self._automation_loop)
        self.automation_thread.daemon = True
        self.automation_thread.start()
        logger.info("Started multi-app automation")
        return True

    def stop_automation(self):
        """Stop the automation process."""
        try:
            if self.running:
                logger.info("Stopping automation...")
                self.running = False
                # Wait for automation thread to finish
                if self.automation_thread and self.automation_thread.is_alive():
                    self.automation_thread.join(timeout=5)
                # Reset timers
                self.last_youtube_action = 0
                self.last_apple_action = 0
                self.last_amazon_action = 0
                self.last_youtube_isoclipboard = 0
                self.last_apple_isoclipboard = 0
                self.last_amazon_isoclipboard = 0
                logger.info("Automation stopped successfully")
            else:
                logger.warning("No automation running to stop")
        except Exception as e:
            logger.error(f"Failed to stop automation: {e}")
            raise

    def start_youtube_only(self):
        """Start only the YouTube Music automation loop."""
        if self.running or not self.youtube_controller:
            return False
        try:
            if not self._youtube_initial_setup():
                return False
            self.running = True
            self.last_youtube_isoclipboard = time.time()
            self.automation_thread = threading.Thread(target=self._youtube_only_loop)
            self.automation_thread.daemon = True
            self.automation_thread.start()
            logger.info("Started YouTube Music automation")
            return True
        except Exception as e:
            logger.error(f"Error starting YouTube Music automation: {e}")
            return False

    def start_apple_only(self):
        """Start only the Apple Music automation loop."""
        if self.running or not self.apple_controller:
            return False
        try:
            if not self._apple_initial_setup():
                return False
            self.running = True
            self.last_apple_isoclipboard = time.time()
            self.automation_thread = threading.Thread(target=self._apple_only_loop)
            self.automation_thread.daemon = True
            self.automation_thread.start()
            logger.info("Started Apple Music automation")
            return True
        except Exception as e:
            logger.error(f"Error starting Apple Music automation: {e}")
            return False

    def start_amazon_only(self):
        """Start only the Amazon Music automation loop."""
        if self.running or not self.amazon_controller:
            return False
        try:
            if not self._amazon_initial_setup():
                return False
            self.running = True
            self.last_amazon_isoclipboard = time.time()
            self.automation_thread = threading.Thread(target=self._amazon_only_loop)
            self.automation_thread.daemon = True
            self.automation_thread.start()
            logger.info("Started Amazon Music automation")
            return True
        except Exception as e:
            logger.error(f"Error starting Amazon Music automation: {e}")
            return False

    def _youtube_only_loop(self):
        """Handle YouTube Music automation loop."""
        while self.running:
            try:
                current_time = time.time()
                youtube_iso_elapsed = current_time - self.last_youtube_isoclipboard
                if youtube_iso_elapsed >= self.get_isoclipboard_delay("youtube_music"):
                    logger.info("Performing YouTube Music IsoClipboard")
                    if self._run_device_locked(self.youtube_controller.handle_isoclipboard):
                        self.last_youtube_isoclipboard = time.time()
                        self.last_youtube_action = time.time()
                        self._run_device_locked(self.youtube_controller.device.press, "home")
                        logger.info("YouTube Music IsoClipboard successful")

                action, action_name = self.get_youtube_action()
                delay = self.get_music_control_delay("youtube_music")
                time.sleep(delay)
                logger.info(f"Performing YouTube Music action: {action_name}")
                if self._run_device_locked(self.youtube_controller.prepare_for_action):
                    if self._run_device_locked(action):
                        self.last_youtube_action = time.time()
                        self._run_device_locked(self.youtube_controller.device.press, "home")
                        logger.info(f"YouTube Music {action_name} successful")
            except Exception as e:
                logger.error(f"Error in YouTube Music automation: {e}")
                time.sleep(60)

    def _apple_only_loop(self):
        """Handle Apple Music automation loop."""
        while self.running:
            try:
                current_time = time.time()
                apple_iso_elapsed = current_time - self.last_apple_isoclipboard
                if apple_iso_elapsed >= self.get_isoclipboard_delay("apple_music"):
                    logger.info("Performing Apple Music IsoClipboard")
                    if self._run_device_locked(self.apple_controller.handle_isoclipboard):
                        self.last_apple_isoclipboard = time.time()
                        self.last_apple_action = time.time()
                        self._run_device_locked(self.apple_controller.device.press, "home")
                        logger.info("Apple Music IsoClipboard successful")

                action, action_name = self.get_apple_action()
                delay = self.get_music_control_delay("apple_music")
                time.sleep(delay)
                logger.info(f"Performing Apple Music action: {action_name}")
                if self._run_device_locked(self.apple_controller.prepare_for_action):
                    if self._run_device_locked(action):
                        self.last_apple_action = time.time()
                        self._run_device_locked(self.apple_controller.device.press, "home")
                        logger.info(f"Apple Music {action_name} successful")
            except Exception as e:
                logger.error(f"Error in Apple Music automation: {e}")
                time.sleep(60)

    def _amazon_only_loop(self):
        """Handle Amazon Music automation loop."""
        while self.running:
            try:
                current_time = time.time()
                amazon_iso_elapsed = current_time - self.last_amazon_isoclipboard
                if amazon_iso_elapsed >= self.get_isoclipboard_delay("amazon_music"):
                    logger.info("Performing Amazon Music IsoClipboard")
                    if self._run_device_locked(self.amazon_controller.handle_isoclipboard):
                        self.last_amazon_isoclipboard = time.time()
                        self.last_amazon_action = time.time()
                        self._run_device_locked(self.amazon_controller.device.press, "home")
                        logger.info("Amazon Music IsoClipboard successful")

                action, action_name = self.get_amazon_action()
                delay = self.get_music_control_delay("amazon_music")
                time.sleep(delay)
                logger.info(f"Performing Amazon Music action: {action_name}")
                if self._run_device_locked(self.amazon_controller.prepare_for_action):
                    if self._run_device_locked(action):
                        self.last_amazon_action = time.time()
                        self._run_device_locked(self.amazon_controller.device.press, "home")
                        logger.info(f"Amazon Music {action_name} successful")
            except Exception as e:
                logger.error(f"Error in Amazon Music automation: {e}")
                time.sleep(60)