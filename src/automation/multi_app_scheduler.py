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

    def __init__(self, youtube_controller: Optional[YouTubeMusicController] = None,
                 apple_controller: Optional[AppleMusicController] = None,
                 amazon_controller: Optional[AmazonMusicController] = None):
        """Initialize automation with controllers."""
        super().__init__()
        self.youtube_controller = youtube_controller
        self.apple_controller = apple_controller
        self.amazon_controller = amazon_controller
        self.running = False
        self.automation_thread: Optional[threading.Thread] = None

        # Initialize timestamps
        self.last_youtube_action = 0
        self.last_apple_action = 0
        self.last_amazon_action = 0
        self.last_youtube_isoclipboard = 0
        self.last_apple_isoclipboard = 0
        self.last_amazon_isoclipboard = 0

        # Store current delays and next execution times
        self.current_delays = {
            'youtube_music': {
                'iso': {'delay': 0, 'next_time': 0},
                'action': {'delay': 0, 'next_time': 0}
            },
            'apple_music': {
                'iso': {'delay': 0, 'next_time': 0},
                'action': {'delay': 0, 'next_time': 0}
            },
            'amazon_music': {
                'iso': {'delay': 0, 'next_time': 0},
                'action': {'delay': 0, 'next_time': 0}
            }
        }

    @with_device_lock
    def _run_device_locked(self, func: Callable, *args, **kwargs):
        """All UI-interacting calls go here to ensure thread safety."""
        return func(*args, **kwargs)

    def _get_stored_delay(self, app_type: str, action_type: str) -> tuple[int, float]:
        """Get stored delay and next execution time, or generate new ones if not set."""
        current_time = time.time()
        stored = self.current_delays[app_type][action_type]

        if stored['delay'] == 0 or current_time >= stored['next_time']:
            # Generate new delay
            if action_type == 'iso':
                if app_type == "youtube_music":
                    minutes = random.randint(22, 33)
                elif app_type == "apple_music":
                    minutes = random.randint(25, 35)
                else:  # amazon_music
                    minutes = random.randint(27, 37)
                delay = minutes * 60
            else:  # Regular action
                if app_type == "youtube_music":
                    delay = random.randint(45, 6 * 60)
                elif app_type == "apple_music":
                    delay = random.randint(60, 7 * 60)
                else:  # amazon_music
                    delay = random.randint(50, 5 * 60)

            # Store new delay and next execution time
            stored['delay'] = delay
            stored['next_time'] = current_time + delay

            # Log only when generating new delay
            self._log_next_action(app_type, action_type, delay)

        return stored['delay'], stored['next_time']

    def _reset_delay(self, app_type: str, action_type: str):
        """Reset stored delay after action is completed."""
        self.current_delays[app_type][action_type]['delay'] = 0
        self.current_delays[app_type][action_type]['next_time'] = 0

    def _log_next_action(self, app_type: str, action_type: str, delay: int):
        """Log next action time."""
        next_time = time.strftime('%H:%M:%S',
                                  time.localtime(time.time() + delay))
        minutes = delay // 60
        remaining_seconds = delay % 60

        app_name = {
            "youtube_music": "YouTube Music",
            "apple_music": "Apple Music",
            "amazon_music": "Amazon Music"
        }[app_type]

        if action_type == 'iso':
            logger.info(f"Next {app_name} IsoClipboard action in {minutes}m (at {next_time})")
        else:
            if minutes > 0:
                logger.info(f"Next {app_name} action in {minutes}m {remaining_seconds}s (at {next_time})")
            else:
                logger.info(f"Next {app_name} action in {remaining_seconds}s (at {next_time})")

    def get_isoclipboard_delay(self, app_type: str) -> int:
        """Get delay between iso-clipboard actions."""
        delay, _ = self._get_stored_delay(app_type, 'iso')
        return delay

    def get_music_control_delay(self, app_type: str) -> int:
        """Get delay for music-control actions."""
        delay, _ = self._get_stored_delay(app_type, 'action')
        return delay

    def _youtube_initial_setup(self) -> bool:
        """Set up YouTube Music for automation."""
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
        """Set up Apple Music for automation."""
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
        """Set up Amazon Music for automation."""
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
        """Main automation loop with optimized scheduling."""
        while self.running:
            try:
                current_time = time.time()
                # Handle IsoClipboard operations - one check per app
                active_apps = []

                if self.youtube_controller:
                    youtube_iso_elapsed = current_time - self.last_youtube_isoclipboard
                    youtube_delay, youtube_next = self._get_stored_delay("youtube_music", "iso")
                    if youtube_iso_elapsed >= youtube_delay:
                        active_apps.append(('youtube_music', self.youtube_controller))

                if self.apple_controller:
                    apple_iso_elapsed = current_time - self.last_apple_isoclipboard
                    apple_delay, apple_next = self._get_stored_delay("apple_music", "iso")
                    if apple_iso_elapsed >= apple_delay:
                        active_apps.append(('apple_music', self.apple_controller))

                if self.amazon_controller:
                    amazon_iso_elapsed = current_time - self.last_amazon_isoclipboard
                    amazon_delay, amazon_next = self._get_stored_delay("amazon_music", "iso")
                    if amazon_iso_elapsed >= amazon_delay:
                        active_apps.append(('amazon_music', self.amazon_controller))

                # Process due IsoClipboard operations
                for app_type, controller in active_apps:
                    logger.info(f"Performing {app_type} IsoClipboard")
                    if self._run_device_locked(controller.handle_isoclipboard):
                        if app_type == 'youtube_music':
                            self.last_youtube_isoclipboard = time.time()
                            self.last_youtube_action = time.time()
                        elif app_type == 'apple_music':
                            self.last_apple_isoclipboard = time.time()
                            self.last_apple_action = time.time()
                        else:  # amazon_music
                            self.last_amazon_isoclipboard = time.time()
                            self.last_amazon_action = time.time()
                        self._run_device_locked(controller.device.press, "home")
                        logger.info(f"{app_type} IsoClipboard successful")
                        self._reset_delay(app_type, "iso")

                # Determine which app needs action based on elapsed time
                elapsed_times = {
                    'youtube': current_time - self.last_youtube_action if self.youtube_controller else float('inf'),
                    'apple': current_time - self.last_apple_action if self.apple_controller else float('inf'),
                    'amazon': current_time - self.last_amazon_action if self.amazon_controller else float('inf')
                }

                app_to_run = max(elapsed_times.items(), key=lambda x: x[1])[0]

                # Execute single action for chosen app
                if app_to_run == 'youtube' and self.youtube_controller:
                    action, action_name = self.get_youtube_action()
                    delay = self.get_music_control_delay("youtube_music")
                    time.sleep(delay)
                    if self._run_device_locked(self.youtube_controller.prepare_for_action):
                        if self._run_device_locked(action):
                            self.last_youtube_action = time.time()
                            self._run_device_locked(self.youtube_controller.device.press, "home")
                            logger.info(f"YouTube Music {action_name} successful")
                            self._reset_delay("youtube_music", "action")

                elif app_to_run == 'apple' and self.apple_controller:
                    action, action_name = self.get_apple_action()
                    delay = self.get_music_control_delay("apple_music")
                    time.sleep(delay)
                    if self._run_device_locked(self.apple_controller.prepare_for_action):
                        if self._run_device_locked(action):
                            self.last_apple_action = time.time()
                            self._run_device_locked(self.apple_controller.device.press, "home")
                            logger.info(f"Apple Music {action_name} successful")
                            self._reset_delay("apple_music", "action")

                elif app_to_run == 'amazon' and self.amazon_controller:
                    action, action_name = self.get_amazon_action()
                    delay = self.get_music_control_delay("amazon_music")
                    time.sleep(delay)
                    if self._run_device_locked(self.amazon_controller.prepare_for_action):
                        if self._run_device_locked(action):
                            self.last_amazon_action = time.time()
                            self._run_device_locked(self.amazon_controller.device.press, "home")
                            logger.info(f"Amazon Music {action_name} successful")
                            self._reset_delay("amazon_music", "action")

            except Exception as e:
                logger.error(f"Error in automation loop: {e}")
                time.sleep(60)

    def _youtube_only_loop(self):
        """Handle YouTube Music automation."""
        while self.running:
            try:
                current_time = time.time()
                youtube_iso_elapsed = current_time - self.last_youtube_isoclipboard
                youtube_delay, youtube_next = self._get_stored_delay("youtube_music", "iso")

                if youtube_iso_elapsed >= youtube_delay:
                    logger.info("Performing YouTube Music IsoClipboard")
                    if self._run_device_locked(self.youtube_controller.handle_isoclipboard):
                        self.last_youtube_isoclipboard = time.time()
                        self.last_youtube_action = time.time()
                        self._run_device_locked(self.youtube_controller.device.press, "home")
                        logger.info("YouTube Music IsoClipboard successful")
                        self._reset_delay("youtube_music", "iso")

                action, action_name = self.get_youtube_action()
                delay = self.get_music_control_delay("youtube_music")
                time.sleep(delay)
                if self._run_device_locked(self.youtube_controller.prepare_for_action):
                    if self._run_device_locked(action):
                        self.last_youtube_action = time.time()
                        self._run_device_locked(self.youtube_controller.device.press, "home")
                        logger.info(f"YouTube Music {action_name} successful")
                        self._reset_delay("youtube_music", "action")
            except Exception as e:
                logger.error(f"Error in YouTube Music automation: {e}")
                time.sleep(60)

    def _apple_only_loop(self):
        """Handle Apple Music automation."""
        while self.running:
            try:
                current_time = time.time()
                apple_iso_elapsed = current_time - self.last_apple_isoclipboard
                apple_delay, apple_next = self._get_stored_delay("apple_music", "iso")

                if apple_iso_elapsed >= apple_delay:
                    logger.info("Performing Apple Music IsoClipboard")
                    if self._run_device_locked(self.apple_controller.handle_isoclipboard):
                        self.last_apple_isoclipboard = time.time()
                        self.last_apple_action = time.time()
                        self._run_device_locked(self.apple_controller.device.press, "home")
                        logger.info("Apple Music IsoClipboard successful")
                        self._reset_delay("apple_music", "iso")

                action, action_name = self.get_apple_action()
                delay = self.get_music_control_delay("apple_music")
                time.sleep(delay)
                if self._run_device_locked(self.apple_controller.prepare_for_action):
                    if self._run_device_locked(action):
                        self.last_apple_action = time.time()
                        self._run_device_locked(self.apple_controller.device.press, "home")
                        logger.info(f"Apple Music {action_name} successful")
                        self._reset_delay("apple_music", "action")
            except Exception as e:
                logger.error(f"Error in Apple Music automation: {e}")
                time.sleep(60)

    def _amazon_only_loop(self):
        """Handle Amazon Music automation."""
        while self.running:
            try:
                current_time = time.time()
                amazon_iso_elapsed = current_time - self.last_amazon_isoclipboard
                amazon_delay, amazon_next = self._get_stored_delay("amazon_music", "iso")

                if amazon_iso_elapsed >= amazon_delay:
                    logger.info("Performing Amazon Music IsoClipboard")
                    if self._run_device_locked(self.amazon_controller.handle_isoclipboard):
                        self.last_amazon_isoclipboard = time.time()
                        self.last_amazon_action = time.time()
                        self._run_device_locked(self.amazon_controller.device.press, "home")
                        logger.info("Amazon Music IsoClipboard successful")
                        self._reset_delay("amazon_music", "iso")

                action, action_name = self.get_amazon_action()
                delay = self.get_music_control_delay("amazon_music")
                time.sleep(delay)
                if self._run_device_locked(self.amazon_controller.prepare_for_action):
                    if self._run_device_locked(action):
                        self.last_amazon_action = time.time()
                        self._run_device_locked(self.amazon_controller.device.press, "home")
                        logger.info(f"Amazon Music {action_name} successful")
                        self._reset_delay("amazon_music", "action")
            except Exception as e:
                logger.error(f"Error in Amazon Music automation: {e}")
                time.sleep(60)

    def _youtube_apple_loop(self):
        """Handle YouTube Music and Apple Music automation."""
        while self.running:
            try:
                current_time = time.time()

                # Handle YouTube Music IsoClipboard
                youtube_iso_elapsed = current_time - self.last_youtube_isoclipboard
                youtube_delay, youtube_next = self._get_stored_delay("youtube_music", "iso")
                if youtube_iso_elapsed >= youtube_delay:
                    logger.info("Performing YouTube Music IsoClipboard")
                    if self._run_device_locked(self.youtube_controller.handle_isoclipboard):
                        self.last_youtube_isoclipboard = time.time()
                        self.last_youtube_action = time.time()
                        self._run_device_locked(self.youtube_controller.device.press, "home")
                        logger.info("YouTube Music IsoClipboard successful")
                        self._reset_delay("youtube_music", "iso")

                # Handle Apple Music IsoClipboard
                apple_iso_elapsed = current_time - self.last_apple_isoclipboard
                apple_delay, apple_next = self._get_stored_delay("apple_music", "iso")
                if apple_iso_elapsed >= apple_delay:
                    logger.info("Performing Apple Music IsoClipboard")
                    if self._run_device_locked(self.apple_controller.handle_isoclipboard):
                        self.last_apple_isoclipboard = time.time()
                        self.last_apple_action = time.time()
                        self._run_device_locked(self.apple_controller.device.press, "home")
                        logger.info("Apple Music IsoClipboard successful")
                        self._reset_delay("apple_music", "iso")

                # Determine which app needs action based on elapsed time
                youtube_elapsed = current_time - self.last_youtube_action
                apple_elapsed = current_time - self.last_apple_action

                if youtube_elapsed > apple_elapsed:
                    action, action_name = self.get_youtube_action()
                    delay = self.get_music_control_delay("youtube_music")
                    time.sleep(delay)
                    if self._run_device_locked(self.youtube_controller.prepare_for_action):
                        if self._run_device_locked(action):
                            self.last_youtube_action = time.time()
                            self._run_device_locked(self.youtube_controller.device.press, "home")
                            logger.info(f"YouTube Music {action_name} successful")
                            self._reset_delay("youtube_music", "action")
                else:
                    action, action_name = self.get_apple_action()
                    delay = self.get_music_control_delay("apple_music")
                    time.sleep(delay)
                    if self._run_device_locked(self.apple_controller.prepare_for_action):
                        if self._run_device_locked(action):
                            self.last_apple_action = time.time()
                            self._run_device_locked(self.apple_controller.device.press, "home")
                            logger.info(f"Apple Music {action_name} successful")
                            self._reset_delay("apple_music", "action")

            except Exception as e:
                logger.error(f"Error in YouTube & Apple Music automation: {e}")
                time.sleep(60)

    def start_youtube_only(self) -> bool:
        """Start YouTube Music automation."""
        if self.running or not self.youtube_controller:
            return False
        try:
            if not self._youtube_initial_setup():
                return False

            # Initialize delays
            current_time = time.time()
            self.last_youtube_action = current_time
            self.last_youtube_isoclipboard = current_time
            self._get_stored_delay("youtube_music", "iso")
            self._get_stored_delay("youtube_music", "action")

            self.running = True
            self.automation_thread = threading.Thread(target=self._youtube_only_loop)
            self.automation_thread.daemon = True
            self.automation_thread.start()
            logger.info("Started YouTube Music automation")
            return True
        except Exception as e:
            logger.error(f"Error starting YouTube Music automation: {e}")
            return False

    def start_apple_only(self) -> bool:
        """Start Apple Music automation."""
        if self.running or not self.apple_controller:
            return False
        try:
            if not self._apple_initial_setup():
                return False

            # Initialize delays
            current_time = time.time()
            self.last_apple_action = current_time
            self.last_apple_isoclipboard = current_time
            self._get_stored_delay("apple_music", "iso")
            self._get_stored_delay("apple_music", "action")

            self.running = True
            self.automation_thread = threading.Thread(target=self._apple_only_loop)
            self.automation_thread.daemon = True
            self.automation_thread.start()
            logger.info("Started Apple Music automation")
            return True
        except Exception as e:
            logger.error(f"Error starting Apple Music automation: {e}")
            return False

    def start_amazon_only(self) -> bool:
        """Start Amazon Music automation."""
        if self.running or not self.amazon_controller:
            return False
        try:
            if not self._amazon_initial_setup():
                return False

            # Initialize delays
            current_time = time.time()
            self.last_amazon_action = current_time
            self.last_amazon_isoclipboard = current_time
            self._get_stored_delay("amazon_music", "iso")
            self._get_stored_delay("amazon_music", "action")

            self.running = True
            self.automation_thread = threading.Thread(target=self._amazon_only_loop)
            self.automation_thread.daemon = True
            self.automation_thread.start()
            logger.info("Started Amazon Music automation")
            return True
        except Exception as e:
            logger.error(f"Error starting Amazon Music automation: {e}")
            return False

    def start_youtube_apple_automation(self) -> bool:
        """Start automation for YouTube Music and Apple Music."""
        if self.running:
            logger.warning("Automation already running")
            return False

        try:
            if not self.youtube_controller or not self.apple_controller:
                logger.error("Both YouTube Music and Apple Music controllers are required")
                return False

            # Initialize timestamps
            current_time = time.time()
            self.last_youtube_action = current_time
            self.last_apple_action = current_time
            self.last_youtube_isoclipboard = current_time
            self.last_apple_isoclipboard = current_time

            # Setup both apps
            if not self._youtube_initial_setup():
                logger.error("Failed YouTube Music initial setup")
                return False

            if not self._apple_initial_setup():
                logger.error("Failed Apple Music initial setup")
                return False

            # Initialize delays
            self._get_stored_delay("youtube_music", "iso")
            self._get_stored_delay("youtube_music", "action")
            self._get_stored_delay("apple_music", "iso")
            self._get_stored_delay("apple_music", "action")

            # Start automation
            self.running = True
            self.automation_thread = threading.Thread(target=self._youtube_apple_loop)
            self.automation_thread.daemon = True
            self.automation_thread.start()
            logger.info("Started YouTube & Apple Music automation")
            return True

        except Exception as e:
            logger.error(f"Failed to start YouTube & Apple Music automation: {e}")
            return False

    def start_automation(self) -> bool:
        """Start automation for configured apps."""
        if self.running:
            logger.warning("Automation already running")
            return False

        # Check if at least one controller is available
        if not any([self.youtube_controller, self.apple_controller, self.amazon_controller]):
            logger.error("No music controllers available")
            return False

        # Initialize all timers
        current_time = time.time()
        self.last_youtube_action = current_time
        self.last_apple_action = current_time
        self.last_amazon_action = current_time
        self.last_youtube_isoclipboard = current_time
        self.last_apple_isoclipboard = current_time
        self.last_amazon_isoclipboard = current_time

        # Set up active controllers and initialize delays
        if self.youtube_controller:
            if not self._youtube_initial_setup():
                logger.error("Failed YouTube Music initial setup")
                return False
            self._get_stored_delay("youtube_music", "iso")
            self._get_stored_delay("youtube_music", "action")

        if self.apple_controller:
            if not self._apple_initial_setup():
                logger.error("Failed Apple Music initial setup")
                return False
            self._get_stored_delay("apple_music", "iso")
            self._get_stored_delay("apple_music", "action")

        if self.amazon_controller:
            if not self._amazon_initial_setup():
                logger.error("Failed Amazon Music initial setup")
                return False
            self._get_stored_delay("amazon_music", "iso")
            self._get_stored_delay("amazon_music", "action")

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
                # Reset all delays
                for app_type in self.current_delays:
                    for action_type in self.current_delays[app_type]:
                        self.current_delays[app_type][action_type]['delay'] = 0
                        self.current_delays[app_type][action_type]['next_time'] = 0
                logger.info("Automation stopped successfully")
            else:
                logger.warning("No automation running to stop")
        except Exception as e:
            logger.error(f"Failed to stop automation: {e}")
            raise