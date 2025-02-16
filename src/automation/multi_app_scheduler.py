# src/automation/multi_app_scheduler.py

import random
import threading
import time
from typing import Optional, Dict, Tuple, Callable, List, Union
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
        super().__init__()  # Initialize MutexMixin
        self.youtube_controller = youtube_controller
        self.apple_controller = apple_controller
        self.amazon_controller = amazon_controller

        self.running = False
        self.paused = False

        # Thread storage
        self.youtube_thread: Optional[threading.Thread] = None
        self.apple_thread: Optional[threading.Thread] = None
        self.amazon_thread: Optional[threading.Thread] = None

        # Timestamps
        self.next_iso_youtube = 0.0
        self.next_iso_apple = 0.0
        self.next_iso_amazon = 0.0
        self.last_youtube_action = 0.0
        self.last_apple_action = 0.0
        self.last_amazon_action = 0.0

    def _get_action_cluster(self,
                            controller: Union[YouTubeMusicController, AppleMusicController, AmazonMusicController],
                            app_type: str) -> List[Tuple[Callable, str]]:
        """Generate a human-like cluster of 1-4 actions."""
        actions = []

        weighted_actions = [
            (controller.next_track, "Next track", 50),
            (controller.previous_track, "Previous track", 20),
            (controller.like_current_song, "Like song", 30)
        ]

        cluster_weights = {
            1: 45,  # 45% chance of single action
            2: 30,  # 30% chance of two actions
            3: 15,  # 15% chance of three actions
            4: 10  # 10% chance of four actions
        }

        cluster_size = random.choices(
            list(cluster_weights.keys()),
            weights=list(cluster_weights.values())
        )[0]

        if cluster_size > 1:
            weighted_actions[0] = (weighted_actions[0][0], weighted_actions[0][1], 70)

        for _ in range(cluster_size):
            action = random.choices(
                weighted_actions,
                weights=[w[2] for w in weighted_actions]
            )[0]
            actions.append((action[0], action[1]))

            if action[1] == "Like song":
                weighted_actions[0] = (weighted_actions[0][0], weighted_actions[0][1], 80)

        return actions

    def _get_human_delay(self, is_cluster: bool = False) -> int:
        if is_cluster:
            return random.randint(2, 8)

        weights = [
            (60, 180, 40),  # 1-3 minutes: 40% chance
            (181, 300, 30),  # 3-5 minutes: 30% chance
            (301, 480, 20),  # 5-8 minutes: 20% chance
            (481, 720, 10)  # 8-12 minutes: 10% chance
        ]

        selected = random.choices(weights, weights=[w[2] for w in weights])[0]
        return random.randint(selected[0], selected[1])

    def get_isoclipboard_delay(self, app_type: str) -> int:
        base_delays = {
            "youtube": (22, 33),
            "apple": (25, 35),
            "amazon": (27, 37)
        }

        base_min, base_max = base_delays[app_type]
        actual_min = max(base_min - random.randint(0, 3), 15)
        actual_max = base_max + random.randint(0, 5)

        minutes = random.randint(actual_min, actual_max)
        seconds = random.randint(0, 59)
        total_seconds = minutes * 60 + seconds

        next_time = time.strftime('%H:%M:%S', time.localtime(time.time() + total_seconds))
        app_name = {
            "youtube": "YouTube Music",
            "apple": "Apple Music",
            "amazon": "Amazon Music"
        }[app_type]
        logger.info(f"Next {app_name} IsoClipboard in {minutes}m {seconds}s (at {next_time})")
        return total_seconds

    @with_device_lock
    def _check_safe_to_act(self) -> bool:
        """Check if enough time has passed since last action. Uses device lock as it checks all apps."""
        now = time.time()
        last_actions = []

        if self.youtube_controller:
            last_actions.append(self.last_youtube_action)
        if self.apple_controller:
            last_actions.append(self.last_apple_action)
        if self.amazon_controller:
            last_actions.append(self.last_amazon_action)

        if last_actions:
            most_recent = max(last_actions)
            return (now - most_recent) >= 10
        return True

    def _youtube_loop(self):
        """YouTube loop - controller methods handle their own mutex."""
        while self.running and self.youtube_controller:
            try:
                if self.paused:
                    time.sleep(300)
                    continue

                now = time.time()
                delay = None

                if now >= self.next_iso_youtube:
                    if self._check_safe_to_act():
                        logger.info("Performing YouTube Music IsoClipboard")
                        success = self.youtube_controller.handle_isoclipboard()
                        if success:
                            self.youtube_controller.device.press("home")
                            logger.info("YouTube Music IsoClipboard successful")
                        delay = self.get_isoclipboard_delay("youtube")
                        self.next_iso_youtube = time.time() + delay
                        time.sleep(random.randint(5, 15))
                        continue

                if self._check_safe_to_act():
                    actions = self._get_action_cluster(self.youtube_controller, "youtube")

                    for action, action_name in actions:
                        if action():  # Controller methods handle their own mutex
                            self.last_youtube_action = time.time()
                            self.youtube_controller.device.press("home")
                            logger.info(f"YouTube Music {action_name} successful")

                            if len(actions) > 1:
                                time.sleep(self._get_human_delay(is_cluster=True))

                delay = self._get_human_delay(is_cluster=False)
                time.sleep(delay)

            except Exception as e:
                logger.error(f"Error in YouTube loop: {e}")
                time.sleep(60)

    def _apple_loop(self):
        """Apple loop - controller methods handle their own mutex."""
        while self.running and self.apple_controller:
            try:
                if self.paused:
                    time.sleep(300)
                    continue

                now = time.time()
                delay = None

                if now >= self.next_iso_apple:
                    if self._check_safe_to_act():
                        logger.info("Performing Apple Music IsoClipboard")
                        success = self.apple_controller.handle_isoclipboard()
                        if success:
                            self.apple_controller.device.press("home")
                            logger.info("Apple Music IsoClipboard successful")
                        delay = self.get_isoclipboard_delay("apple")
                        self.next_iso_apple = time.time() + delay
                        time.sleep(random.randint(5, 15))
                        continue

                if self._check_safe_to_act():
                    actions = self._get_action_cluster(self.apple_controller, "apple")

                    for action, action_name in actions:
                        if action():  # Controller methods handle their own mutex
                            self.last_apple_action = time.time()
                            self.apple_controller.device.press("home")
                            logger.info(f"Apple Music {action_name} successful")

                            if len(actions) > 1:
                                time.sleep(self._get_human_delay(is_cluster=True))

                delay = self._get_human_delay(is_cluster=False)
                time.sleep(delay)

            except Exception as e:
                logger.error(f"Error in Apple loop: {e}")
                time.sleep(60)

    def _amazon_loop(self):
        """Amazon loop - controller methods handle their own mutex."""
        while self.running and self.amazon_controller:
            try:
                if self.paused:
                    time.sleep(300)
                    continue

                now = time.time()
                delay = None

                if now >= self.next_iso_amazon:
                    if self._check_safe_to_act():
                        logger.info("Performing Amazon Music IsoClipboard")
                        success = self.amazon_controller.handle_isoclipboard()
                        if success:
                            self.amazon_controller.device.press("home")
                            logger.info("Amazon Music IsoClipboard successful")
                        delay = self.get_isoclipboard_delay("amazon")
                        self.next_iso_amazon = time.time() + delay
                        time.sleep(random.randint(5, 15))
                        continue

                if self._check_safe_to_act():
                    actions = self._get_action_cluster(self.amazon_controller, "amazon")

                    for action, action_name in actions:
                        if action():  # Controller methods handle their own mutex
                            self.last_amazon_action = time.time()
                            self.amazon_controller.device.press("home")
                            logger.info(f"Amazon Music {action_name} successful")

                            if len(actions) > 1:
                                time.sleep(self._get_human_delay(is_cluster=True))

                delay = self._get_human_delay(is_cluster=False)
                time.sleep(delay)

            except Exception as e:
                logger.error(f"Error in Amazon loop: {e}")
                time.sleep(60)

    @with_device_lock
    def _youtube_initial_setup(self) -> bool:
        """Initial setup needs device lock as it's preparing the device state."""
        logger.info("Starting YouTube Music initial setup...")
        try:
            if not self.youtube_controller.force_stop():
                logger.error("Failed to close YT Music")
                return False
            time.sleep(2)

            if not self.youtube_controller.handle_isoclipboard():
                logger.error("YT Music iso-clipboard setup failed")
                return False

            if not self.youtube_controller.manage_window_state(True):
                logger.warning("Failed to minimize YT window")

            logger.info("YouTube Music initial setup completed")
            return True
        except Exception as e:
            logger.error(f"Error in YouTube init setup: {e}")
            return False

    @with_device_lock
    def _apple_initial_setup(self) -> bool:
        """Initial setup needs device lock as it's preparing the device state."""
        logger.info("Starting Apple Music initial setup...")
        try:
            if not self.apple_controller.force_stop():
                logger.warning("Failed to close Apple Music")
            time.sleep(2)

            if not self.apple_controller.handle_isoclipboard():
                logger.error("Apple Music iso-clipboard setup failed")
                return False

            if not self.apple_controller.manage_window_state(True):
                logger.warning("Failed to minimize Apple Music window")

            logger.info("Apple Music initial setup completed")
            return True
        except Exception as e:
            logger.error(f"Error in Apple init setup: {e}")
            return False

    @with_device_lock
    def _amazon_initial_setup(self) -> bool:
        """Initial setup needs device lock as it's preparing the device state."""
        logger.info("Starting Amazon Music initial setup...")
        try:
            if not self.amazon_controller.force_stop():
                logger.warning("Failed to close Amazon Music")
            time.sleep(2)

            if not self.amazon_controller.handle_isoclipboard():
                logger.error("Amazon Music iso-clipboard setup failed")
                return False

            if not self.amazon_controller.manage_window_state(True):
                logger.warning("Failed to minimize Amazon Music window")

            logger.info("Amazon Music initial setup completed")
            return True
        except Exception as e:
            logger.error(f"Error in Amazon init setup: {e}")
            return False

    def start_automation(self) -> bool:
        """Start automation for all available controllers."""
        if self.running:
            logger.warning("Automation already running")
            return False

        controllers_available = any([
            self.youtube_controller,
            self.apple_controller,
            self.amazon_controller
        ])
        if not controllers_available:
            logger.error("No music controllers available")
            return False

        # Initial setups are device-locked internally
        if self.youtube_controller and not self._youtube_initial_setup():
            return False
        if self.apple_controller and not self._apple_initial_setup():
            return False
        if self.amazon_controller and not self._amazon_initial_setup():
            return False

        now = time.time()
        self.running = True

        if self.youtube_controller:
            self.next_iso_youtube = now + self.get_isoclipboard_delay("youtube")
            self.last_youtube_action = now
            self.youtube_thread = threading.Thread(target=self._youtube_loop, daemon=True)
            self.youtube_thread.start()
            logger.info("Launched YouTube Music automation thread")

        if self.apple_controller:
            self.next_iso_apple = now + self.get_isoclipboard_delay("apple")
            self.last_apple_action = now
            self.apple_thread = threading.Thread(target=self._apple_loop, daemon=True)
            self.apple_thread.start()
            logger.info("Launched Apple Music automation thread")

        if self.amazon_controller:
            self.next_iso_amazon = now + self.get_isoclipboard_delay("amazon")
            self.last_amazon_action = now
            self.amazon_thread = threading.Thread(target=self._amazon_loop, daemon=True)
            self.amazon_thread.start()
            logger.info("Launched Amazon Music automation thread")

        logger.info("All requested automation threads started")
        return True

    def stop_automation(self):
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
            now = time.time()
            self.next_iso_youtube = now + self.get_isoclipboard_delay("youtube")
            self.last_youtube_action = now

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
            now = time.time()
            self.next_iso_apple = now + self.get_isoclipboard_delay("apple")
            self.last_apple_action = now

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
            now = time.time()
            self.next_iso_amazon = now + self.get_isoclipboard_delay("amazon")
            self.last_amazon_action = now

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

    def get_status(self) -> dict:
        """Get detailed automation status."""
        status = {
            "running": self.running,
            "paused": self.paused,
            "active_apps": []
        }

        if self.youtube_controller:
            status["active_apps"].append("YouTube Music")
            if self.last_youtube_action > 0:
                status["last_youtube_action"] = time.strftime('%H:%M:%S',
                                                              time.localtime(self.last_youtube_action))
            if self.next_iso_youtube > 0:
                status["next_youtube_iso"] = time.strftime('%H:%M:%S',
                                                           time.localtime(self.next_iso_youtube))

        if self.apple_controller:
            status["active_apps"].append("Apple Music")
            if self.last_apple_action > 0:
                status["last_apple_action"] = time.strftime('%H:%M:%S',
                                                            time.localtime(self.last_apple_action))
            if self.next_iso_apple > 0:
                status["next_apple_iso"] = time.strftime('%H:%M:%S',
                                                         time.localtime(self.next_iso_apple))

        if self.amazon_controller:
            status["active_apps"].append("Amazon Music")
            if self.last_amazon_action > 0:
                status["last_amazon_action"] = time.strftime('%H:%M:%S',
                                                             time.localtime(self.last_amazon_action))
            if self.next_iso_amazon > 0:
                status["next_amazon_iso"] = time.strftime('%H:%M:%S',
                                                          time.localtime(self.next_iso_amazon))

        return status