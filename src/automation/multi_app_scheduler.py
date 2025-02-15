# src/automation/multi_app_scheduler.py

import random
import threading
import time
from typing import Optional, Tuple, Callable
from src.utils.logging_utils import setup_logger
from src.controllers.app_controllers.youtube_music import YouTubeMusicController
from src.controllers.app_controllers.apple_music import AppleMusicController
from src.controllers.app_controllers.amazon_music import AmazonMusicController
from src.controllers.mutex_mixin import MutexMixin, with_device_lock

logger = setup_logger(__name__)


class MultiMusicAutomation(MutexMixin):

    def __init__(
        self,
        youtube_controller: Optional[YouTubeMusicController] = None,
        apple_controller: Optional[AppleMusicController] = None,
        amazon_controller: Optional[AmazonMusicController] = None
    ):
        super().__init__()  # Initialize Mutex
        self.youtube_controller = youtube_controller
        self.apple_controller = apple_controller
        self.amazon_controller = amazon_controller

        self.running = False
        self.paused = False

        # We will store one thread per active app
        self.youtube_thread: Optional[threading.Thread] = None
        self.apple_thread: Optional[threading.Thread] = None
        self.amazon_thread: Optional[threading.Thread] = None

        # Timestamps for IsoClipboard scheduling
        self.next_iso_youtube = 0.0
        self.next_iso_apple = 0.0
        self.next_iso_amazon = 0.0

        # Timestamps for last action
        self.last_youtube_action = 0.0
        self.last_apple_action = 0.0
        self.last_amazon_action = 0.0

    @with_device_lock
    def _run_locked(self, func: Callable, *args, **kwargs):
        return func(*args, **kwargs)

    def get_isoclipboard_delay(self, app_type: str) -> int:
        if app_type == "youtube":
            minutes = random.randint(22, 33)
            app_name = "YouTube Music"
        elif app_type == "apple":
            minutes = random.randint(25, 35)
            app_name = "Apple Music"
        else:
            minutes = random.randint(27, 37)
            app_name = "Amazon Music"

        seconds = minutes * 60
        next_time = time.strftime('%H:%M:%S', time.localtime(time.time() + seconds))
        logger.info(f"Next {app_name} IsoClipboard action in {minutes}m (at {next_time})")
        return seconds

    def get_music_action_delay(self, app_type: str) -> int:

        if app_type == "youtube":
            seconds = random.randint(45, 6 * 60)
            app_name = "YouTube Music"
        elif app_type == "apple":
            seconds = random.randint(60, 7 * 60)
            app_name = "Apple Music"
        else:
            seconds = random.randint(50, 5 * 60)
            app_name = "Amazon Music"

        m = seconds // 60
        s = seconds % 60
        next_time = time.strftime('%H:%M:%S', time.localtime(time.time() + seconds))

        if m:
            logger.info(f"Next {app_name} action in {m}m {s}s (at {next_time})")
        else:
            logger.info(f"Next {app_name} action in {seconds}s (at {next_time})")
        return seconds

    def _youtube_loop(self):
        while self.running and self.youtube_controller:
            try:
                if self.paused:
                    time.sleep(1)
                    continue

                # 1) IsoClipboard check
                now = time.time()
                if now >= self.next_iso_youtube:
                    logger.info("Performing YouTube Music IsoClipboard")
                    success = self._run_locked(self.youtube_controller.handle_isoclipboard)
                    if success:
                        # Press home
                        self._run_locked(self.youtube_controller.device.press, "home")
                        logger.info("YouTube Music IsoClipboard successful")

                    # Schedule next iso-clipboard
                    delay = self.get_isoclipboard_delay("youtube")
                    self.next_iso_youtube = time.time() + delay

                # 2) Wait random time, do random music action
                action_delay = self.get_music_action_delay("youtube")
                time.sleep(action_delay)

                # 3) Perform random action (like/next/prev)
                action, action_name = self.get_youtube_action()
                if self._run_locked(action):
                    self.last_youtube_action = time.time()
                    self._run_locked(self.youtube_controller.device.press, "home")
                    logger.info(f"YouTube Music {action_name} successful")

            except Exception as e:
                logger.error(f"Error in YouTube loop: {e}")
                time.sleep(60)

    def _apple_loop(self):
        while self.running and self.apple_controller:
            try:
                if self.paused:
                    time.sleep(1)
                    continue

                # 1) IsoClipboard check
                now = time.time()
                if now >= self.next_iso_apple:
                    logger.info("Performing Apple Music IsoClipboard")
                    success = self._run_locked(self.apple_controller.handle_isoclipboard)
                    if success:
                        self._run_locked(self.apple_controller.device.press, "home")
                        logger.info("Apple Music IsoClipboard successful")

                    # Reschedule next iso-clipboard
                    delay = self.get_isoclipboard_delay("apple")
                    self.next_iso_apple = time.time() + delay

                # 2) Wait random time, do random music action
                action_delay = self.get_music_action_delay("apple")
                time.sleep(action_delay)

                # 3) Perform random action
                action, action_name = self.get_apple_action()
                if self._run_locked(action):
                    self.last_apple_action = time.time()
                    self._run_locked(self.apple_controller.device.press, "home")
                    logger.info(f"Apple Music {action_name} successful")

            except Exception as e:
                logger.error(f"Error in Apple loop: {e}")
                time.sleep(60)

    def _amazon_loop(self):
        while self.running and self.amazon_controller:
            try:
                if self.paused:
                    time.sleep(1)
                    continue

                # 1) IsoClipboard check
                now = time.time()
                if now >= self.next_iso_amazon:
                    logger.info("Performing Amazon Music IsoClipboard")
                    success = self._run_locked(self.amazon_controller.handle_isoclipboard)
                    if success:
                        self._run_locked(self.amazon_controller.device.press, "home")
                        logger.info("Amazon Music IsoClipboard successful")

                    # Reschedule next iso-clipboard
                    delay = self.get_isoclipboard_delay("amazon")
                    self.next_iso_amazon = time.time() + delay

                # 2) Wait random time, do random music action
                action_delay = self.get_music_action_delay("amazon")
                time.sleep(action_delay)

                # 3) Perform random action
                action, action_name = self.get_amazon_action()
                if self._run_locked(action):
                    self.last_amazon_action = time.time()
                    self._run_locked(self.amazon_controller.device.press, "home")
                    logger.info(f"Amazon Music {action_name} successful")

            except Exception as e:
                logger.error(f"Error in Amazon loop: {e}")
                time.sleep(60)


    def get_youtube_action(self) -> Tuple[Callable, str]:
        actions = [
            (self.youtube_controller.next_track, "Next track"),
            (self.youtube_controller.like_current_song, "Like song"),
            (self.youtube_controller.previous_track, "Previous track"),
        ]
        return random.choice(actions)

    def get_apple_action(self) -> Tuple[Callable, str]:
        actions = [
            (self.apple_controller.next_track, "Next track"),
            (self.apple_controller.like_current_song, "Like song"),
            (self.apple_controller.previous_track, "Previous track"),
        ]
        return random.choice(actions)

    def get_amazon_action(self) -> Tuple[Callable, str]:
        actions = [
            (self.amazon_controller.next_track, "Next track"),
            (self.amazon_controller.like_current_song, "Like song"),
            (self.amazon_controller.previous_track, "Previous track"),
        ]
        return random.choice(actions)

    def _youtube_initial_setup(self) -> bool:
        logger.info("Starting YouTube Music initial setup...")
        try:
            if not self._run_locked(self.youtube_controller.force_stop):
                logger.error("Failed to close YT Music")
                return False
            time.sleep(2)

            if not self._run_locked(self.youtube_controller.handle_isoclipboard):
                logger.error("YT Music iso-clipboard setup failed")
                return False

            # Minimize
            if not self._run_locked(self.youtube_controller.manage_window_state, True):
                logger.warning("Failed to minimize YT window")

            logger.info("YouTube Music initial setup completed")
            return True
        except Exception as e:
            logger.error(f"Error in YouTube init setup: {e}")
            return False

    def _apple_initial_setup(self) -> bool:
        logger.info("Starting Apple Music initial setup...")
        try:
            if not self._run_locked(self.apple_controller.force_stop):
                logger.warning("Failed to close Apple Music")
            time.sleep(2)

            if not self._run_locked(self.apple_controller.handle_isoclipboard):
                logger.error("Apple Music iso-clipboard setup failed")
                return False

            if not self._run_locked(self.apple_controller.manage_window_state, True):
                logger.warning("Failed to minimize Apple Music window")

            logger.info("Apple Music initial setup completed")
            return True
        except Exception as e:
            logger.error(f"Error in Apple init setup: {e}")
            return False

    def _amazon_initial_setup(self) -> bool:
        logger.info("Starting Amazon Music initial setup...")
        try:
            if not self._run_locked(self.amazon_controller.force_stop):
                logger.warning("Failed to close Amazon Music")
            time.sleep(2)

            if not self._run_locked(self.amazon_controller.handle_isoclipboard):
                logger.error("Amazon Music iso-clipboard setup failed")
                return False

            if not self._run_locked(self.amazon_controller.manage_window_state, True):
                logger.warning("Failed to minimize Amazon Music window")

            logger.info("Amazon Music initial setup completed")
            return True
        except Exception as e:
            logger.error(f"Error in Amazon init setup: {e}")
            return False

    def start_automation(self) -> bool:
        """
        Start multi-threaded automation for whichever controllers are not None.
        Each app has its own thread loop that handles iso-clipboard + music actions.
        """
        if self.running:
            logger.warning("Automation already running")
            return False

        # Check if there's at least one controller
        controllers_available = any([
            self.youtube_controller,
            self.apple_controller,
            self.amazon_controller
        ])
        if not controllers_available:
            logger.error("No music controllers available")
            return False

        # Perform initial setups
        if self.youtube_controller:
            if not self._youtube_initial_setup():
                return False
        if self.apple_controller:
            if not self._apple_initial_setup():
                return False
        if self.amazon_controller:
            if not self._amazon_initial_setup():
                return False

        # Mark running
        self.running = True

        # Initialize next iso times so each loop doesn't do iso-clipboard instantly
        now = time.time()
        if self.youtube_controller:
            self.next_iso_youtube = now + self.get_isoclipboard_delay("youtube")
        if self.apple_controller:
            self.next_iso_apple = now + self.get_isoclipboard_delay("apple")
        if self.amazon_controller:
            self.next_iso_amazon = now + self.get_isoclipboard_delay("amazon")

        # Launch separate threads for each active controller
        if self.youtube_controller:
            self.youtube_thread = threading.Thread(target=self._youtube_loop, daemon=True)
            self.youtube_thread.start()
            logger.info("Launched YouTube Music automation thread")

        if self.apple_controller:
            self.apple_thread = threading.Thread(target=self._apple_loop, daemon=True)
            self.apple_thread.start()
            logger.info("Launched Apple Music automation thread")

        if self.amazon_controller:
            self.amazon_thread = threading.Thread(target=self._amazon_loop, daemon=True)
            self.amazon_thread.start()
            logger.info("Launched Amazon Music automation thread")

        logger.info("All requested automation threads started")
        return True

    def stop_automation(self):
        """
        Signal all threads to stop and wait for them to finish.
        """
        if not self.running:
            logger.warning("No automation is currently running to stop.")
            return

        logger.info("Stopping automation...")
        self.running = False

        # Join each thread if it's alive
        if self.youtube_thread and self.youtube_thread.is_alive():
            self.youtube_thread.join(timeout=5)
            self.youtube_thread = None

        if self.apple_thread and self.apple_thread.is_alive():
            self.apple_thread.join(timeout=5)
            self.apple_thread = None

        if self.amazon_thread and self.amazon_thread.is_alive():
            self.amazon_thread.join(timeout=5)
            self.amazon_thread = None

        # Reset times, etc.
        self.next_iso_youtube = 0
        self.next_iso_apple = 0
        self.next_iso_amazon = 0
        self.last_youtube_action = 0
        self.last_apple_action = 0
        self.last_amazon_action = 0

        logger.info("Automation stopped successfully.")

    def start_youtube_only(self) -> bool:
        """Start automation for YouTube Music only."""
        try:
            if not self.youtube_controller:
                logger.error("No YouTube Music controller available")
                return False

            if not self._youtube_initial_setup():
                return False

            self.running = True
            self.next_iso_youtube = time.time() + self.get_isoclipboard_delay("youtube")

            self.youtube_thread = threading.Thread(target=self._youtube_loop, daemon=True)
            self.youtube_thread.start()
            logger.info("YouTube Music automation thread started")

            return True
        except Exception as e:
            logger.error(f"Error starting YouTube Music automation: {e}")
            self.running = False
            return False

    def start_apple_only(self) -> bool:
        """Start automation for Apple Music only."""
        try:
            if not self.apple_controller:
                logger.error("No Apple Music controller available")
                return False

            if not self._apple_initial_setup():
                return False

            self.running = True
            self.next_iso_apple = time.time() + self.get_isoclipboard_delay("apple")

            self.apple_thread = threading.Thread(target=self._apple_loop, daemon=True)
            self.apple_thread.start()
            logger.info("Apple Music automation thread started")

            return True
        except Exception as e:
            logger.error(f"Error starting Apple Music automation: {e}")
            self.running = False
            return False

    def start_amazon_only(self) -> bool:
        """Start automation for Amazon Music only."""
        try:
            if not self.amazon_controller:
                logger.error("No Amazon Music controller available")
                return False

            if not self._amazon_initial_setup():
                return False

            self.running = True
            self.next_iso_amazon = time.time() + self.get_isoclipboard_delay("amazon")

            self.amazon_thread = threading.Thread(target=self._amazon_loop, daemon=True)
            self.amazon_thread.start()
            logger.info("Amazon Music automation thread started")

            return True
        except Exception as e:
            logger.error(f"Error starting Amazon Music automation: {e}")
            self.running = False
            return False

    def pause_automation(self) -> bool:
        """Pause running automation."""
        try:
            if not self.running:
                logger.warning("No automation is currently running")
                return False
            if self.paused:
                logger.warning("Automation is already paused")
                return False
            logger.info("Pausing automation...")
            self.paused = True
            return True
        except Exception as e:
            logger.error(f"Error pausing automation: {e}")
            return False

    def resume_automation(self) -> bool:
        """Resume paused automation."""
        try:
            if not self.running:
                logger.warning("No automation is currently running")
                return False
            if not self.paused:
                logger.warning("Automation is not paused")
                return False
            logger.info("Resuming automation...")
            self.paused = False
            return True
        except Exception as e:
            logger.error(f"Error resuming automation: {e}")
            return False