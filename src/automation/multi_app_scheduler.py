# src/automation/multi_app_scheduler.py

import random
import threading
import time
from typing import Optional, Tuple, Callable, List, Union
from src.utils.logging_utils import setup_logger
from src.controllers.app_controllers.youtube_music import YouTubeMusicController
from src.controllers.app_controllers.apple_music import AppleMusicController
from src.controllers.app_controllers.amazon_music import AmazonMusicController
from src.controllers.mutex_mixin import MutexMixin

logger = setup_logger(__name__)


class MultiMusicAutomation(MutexMixin):
    def __init__(
        self,
        youtube_controller: Optional[YouTubeMusicController] = None,
        apple_controller: Optional[AppleMusicController] = None,
        amazon_controller: Optional[AmazonMusicController] = None
    ):
        super().__init__()
        self.youtube_controller = youtube_controller
        self.apple_controller = apple_controller
        self.amazon_controller = amazon_controller
        self.running = False
        self.paused = False

        # Threads
        self.youtube_thread: Optional[threading.Thread] = None
        self.apple_thread: Optional[threading.Thread] = None
        self.amazon_thread: Optional[threading.Thread] = None

        # Next IsoClipboard timestamps
        self.next_iso_youtube = 0.0
        self.next_iso_apple = 0.0
        self.next_iso_amazon = 0.0

        # Last action timestamps
        self.last_youtube_action = 0.0
        self.last_apple_action = 0.0
        self.last_amazon_action = 0.0

        # Lock for coordinating actions
        self.action_lock = threading.Lock()

    def _get_action_cluster(
        self,
        controller: Union[YouTubeMusicController, AppleMusicController, AmazonMusicController],
        app_type: str
    ) -> List[Tuple[Callable, str]]:
        """
        Generate a cluster of 1-4 actions in a “human-like” sequence.
        Weighted chance of Next track, Previous track, or Like song.
        """
        actions = []

        weighted_actions = [
            (controller.next_track, "Next track", 50),
            (controller.previous_track, "Previous track", 20),
            (controller.like_current_song, "Like song", 30),
        ]

        cluster_weights = {
            1: 50,  # 50% chance of doing just 1 action
            2: 30,
            3: 15,
            4: 5
        }

        cluster_size = random.choices(
            list(cluster_weights.keys()),
            weights=list(cluster_weights.values())
        )[0]

        # If we have more than 1 action in the cluster, increase chance
        # of “Next track”.
        if cluster_size > 1:
            weighted_actions[0] = (weighted_actions[0][0], weighted_actions[0][1], 70)

        for _ in range(cluster_size):
            action = random.choices(
                weighted_actions,
                weights=[w[2] for w in weighted_actions]
            )[0]
            actions.append((action[0], action[1]))

            # If we get a "Like song", boost the chance
            # of "Next track" even more.
            if action[1] == "Like song":
                weighted_actions[0] = (weighted_actions[0][0], weighted_actions[0][1], 80)

        return actions

    def _get_human_delay(self, is_cluster: bool = False) -> int:
        """
        Return a random delay to simulate "human" waiting.
        is_cluster=True means we’re waiting between actions within
        one cluster, so use a smaller range.
        """
        if is_cluster:
            return random.randint(15, 25)  # e.g. 15–25s between cluster steps

        # Otherwise, random wait in these brackets (in seconds):
        # 3-5 mins (40%), 5-8 mins (30%), 8-12 mins (20%), 12-15 mins(10%).
        weights = [
            (180, 300, 40),  # 3-5 minutes
            (301, 480, 30),  # 5-8 minutes
            (481, 720, 20),  # 8-12 minutes
            (721, 900, 10)   # 12-15 minutes
        ]
        chosen_range = random.choices(weights, weights=[w[2] for w in weights])[0]
        return random.randint(chosen_range[0], chosen_range[1])

    def get_isoclipboard_delay(self, app_type: str) -> int:
        """
        Compute a random time until the next IsoClipboard usage,
        depending on app_type. E.g. YT: 22–33m, Apple: 25–35m, Amazon: 27–37m.
        """
        base_delays = {
            "youtube": (22, 33),
            "apple": (25, 35),
            "amazon": (27, 37)
        }
        base_min, base_max = base_delays[app_type]

        # Add some randomness +/- 0–3 to the min, +0–5 to the max, but never < 15
        actual_min = max(base_min - random.randint(0, 3), 15)
        actual_max = base_max + random.randint(0, 5)

        minutes = random.randint(actual_min, actual_max)
        seconds = random.randint(0, 59)
        total_seconds = minutes * 60 + seconds

        next_time_str = time.strftime(
            '%H:%M:%S',
            time.localtime(time.time() + total_seconds)
        )
        app_name = {
            "youtube": "YouTube Music",
            "apple": "Apple Music",
            "amazon": "Amazon Music"
        }[app_type]
        logger.info(f"Next {app_name} IsoClipboard in {minutes}m {seconds}s (at {next_time_str})")
        return total_seconds

    def _check_safe_to_act(self) -> bool:
        """
        Check if enough time (15s) has passed since the last action from ANY app.
        This ensures we don't do Apple action 2s after a YouTube action, etc.
        """
        now = time.time()
        with self.action_lock:
            timestamps = []
            if self.youtube_controller:
                timestamps.append(self.last_youtube_action)
            if self.apple_controller:
                timestamps.append(self.last_apple_action)
            if self.amazon_controller:
                timestamps.append(self.last_amazon_action)

            if not timestamps:
                # If no controllers or no last actions, safe to act
                return True

            most_recent = max(timestamps)
            return (now - most_recent) >= 15  # at least 15s since last action

    def _set_last_action(self, app_type: str, timestamp: float):
        """Update the last action time for the given app type, thread-safe."""
        with self.action_lock:
            if app_type == "youtube":
                self.last_youtube_action = timestamp
            elif app_type == "apple":
                self.last_apple_action = timestamp
            elif app_type == "amazon":
                self.last_amazon_action = timestamp

    def _ensure_minimized(self, controller: Union[YouTubeMusicController, AppleMusicController, AmazonMusicController]):
        """
        Press HOME and manage window state, with a short delay,
        to ensure the app is truly minimized.
        """
        controller.device.press("home")
        controller.manage_window_state(True)
        time.sleep(1)

    def _execute_action_cluster(
        self,
        controller: Union[YouTubeMusicController, AppleMusicController, AmazonMusicController],
        actions: List[Tuple[Callable, str]],
        app_type: str
    ) -> bool:
        """
        Execute a cluster of 1–4 actions for an app, ensuring
        we wait 15s from the last action, etc.
        """
        for (action, action_name) in actions:
            # Wait for the safe gap
            if not self._check_safe_to_act():
                logger.info(f"Skipping {app_type} {action_name} - too soon after last action")
                return False

            # Attempt the action
            with self.action_lock:
                success = action()
                if success:
                    # Mark last action time
                    self._set_last_action(app_type, time.time())

                    # Immediately minimize the app after the single action
                    controller.device.press("home")
                    controller.manage_window_state(True)
                    time.sleep(1)

                    logger.info(f"{app_type} {action_name} successful")

                    # If multiple actions in the cluster, do a shorter wait between them
                    if len(actions) > 1:
                        time.sleep(self._get_human_delay(is_cluster=True))
                else:
                    logger.warning(f"{app_type} {action_name} failed")
                    return False
        return True

    def _youtube_loop(self):
        """Main loop for YouTube Music automation."""
        while self.running and self.youtube_controller:
            try:
                if self.paused:
                    # If paused, sleep 5 minutes, then check again
                    time.sleep(300)
                    continue

                now = time.time()

                # Check if it's time for an IsoClipboard run
                if now >= self.next_iso_youtube and self._check_safe_to_act():
                    with self.action_lock:
                        logger.info("Performing YouTube Music IsoClipboard")
                        if self.youtube_controller.handle_isoclipboard():
                            self._ensure_minimized(self.youtube_controller)
                            logger.info("YouTube Music IsoClipboard successful")

                            # Schedule next iso
                            self.next_iso_youtube = time.time() + self.get_isoclipboard_delay("youtube")
                            time.sleep(random.randint(5, 15))
                        # continue to next iteration
                    continue

                # Otherwise, do a small cluster of actions if it's safe
                if self._check_safe_to_act():
                    actions = self._get_action_cluster(self.youtube_controller, "youtube")
                    self._execute_action_cluster(self.youtube_controller, actions, "youtube")

                # Sleep the big "human" delay
                time.sleep(self._get_human_delay(is_cluster=False))

            except Exception as e:
                logger.error(f"Error in YouTube loop: {e}")
                time.sleep(60)

    def _apple_loop(self):
        """Main loop for Apple Music automation."""
        while self.running and self.apple_controller:
            try:
                if self.paused:
                    time.sleep(300)
                    continue

                now = time.time()

                # Check if time for IsoClipboard
                if now >= self.next_iso_apple and self._check_safe_to_act():
                    with self.action_lock:
                        logger.info("Performing Apple Music IsoClipboard")
                        if self.apple_controller.handle_isoclipboard():
                            self._ensure_minimized(self.apple_controller)
                            logger.info("Apple Music IsoClipboard successful")

                            self.next_iso_apple = time.time() + self.get_isoclipboard_delay("apple")
                            time.sleep(random.randint(5, 15))
                        continue

                # Otherwise, do a cluster
                if self._check_safe_to_act():
                    actions = self._get_action_cluster(self.apple_controller, "apple")
                    self._execute_action_cluster(self.apple_controller, actions, "apple")

                time.sleep(self._get_human_delay(is_cluster=False))

            except Exception as e:
                logger.error(f"Error in Apple loop: {e}")
                time.sleep(60)

    def _amazon_loop(self):
        """Main loop for Amazon Music automation."""
        while self.running and self.amazon_controller:
            try:
                if self.paused:
                    time.sleep(300)
                    continue

                now = time.time()

                # IsoClipboard check
                if now >= self.next_iso_amazon and self._check_safe_to_act():
                    with self.action_lock:
                        logger.info("Performing Amazon Music IsoClipboard")
                        if self.amazon_controller.handle_isoclipboard():
                            self._ensure_minimized(self.amazon_controller)
                            logger.info("Amazon Music IsoClipboard successful")

                            self.next_iso_amazon = time.time() + self.get_isoclipboard_delay("amazon")
                            time.sleep(random.randint(5, 15))
                        continue

                # Otherwise do cluster
                if self._check_safe_to_act():
                    actions = self._get_action_cluster(self.amazon_controller, "amazon")
                    self._execute_action_cluster(self.amazon_controller, actions, "amazon")

                time.sleep(self._get_human_delay(is_cluster=False))

            except Exception as e:
                logger.error(f"Error in Amazon loop: {e}")
                time.sleep(60)

    def _youtube_initial_setup(self) -> bool:
        """One-time initial setup for YT Music."""
        logger.info("Starting YouTube Music initial setup...")
        try:
            if not self.youtube_controller.force_stop():
                logger.error("Failed to close YT Music")
                return False
            time.sleep(2)

            # Do an iso-clipboard pass as part of the init
            if not self.youtube_controller.handle_isoclipboard():
                logger.error("YT Music iso-clipboard setup failed")
                return False

            # Minimize
            if not self.youtube_controller.manage_window_state(True):
                logger.warning("Failed to minimize YT window")

            logger.info("YouTube Music initial setup completed")
            return True
        except Exception as e:
            logger.error(f"Error in YouTube init setup: {e}")
            return False

    def _apple_initial_setup(self) -> bool:
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

    def _amazon_initial_setup(self) -> bool:
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
        """
        Start automation for all available controllers.
        Runs initial setups for each (sequentially, with 5s gap),
        then starts each app loop in its own thread.
        """
        if self.running:
            logger.warning("Automation already running")
            return False

        # Check that at least one controller is available
        if not any([self.youtube_controller, self.apple_controller, self.amazon_controller]):
            logger.error("No music controllers available")
            return False

        # Initial setups (sequential)
        if self.youtube_controller:
            if not self._youtube_initial_setup():
                return False
            time.sleep(5)  # short gap

        if self.apple_controller:
            if not self._apple_initial_setup():
                return False
            time.sleep(5)

        if self.amazon_controller:
            if not self._amazon_initial_setup():
                return False

        # Everything set; start threads
        now = time.time()
        self.running = True

        # Stagger iso times so they won't all run exactly together
        if self.youtube_controller:
            self.next_iso_youtube = now + self.get_isoclipboard_delay("youtube")
            self.last_youtube_action = now
            self.youtube_thread = threading.Thread(target=self._youtube_loop, daemon=True)
            self.youtube_thread.start()
            logger.info("Launched YouTube Music automation thread")
            time.sleep(5)

        if self.apple_controller:
            # Add 2 extra minutes to Apple iso start
            self.next_iso_apple = now + self.get_isoclipboard_delay("apple") + 120
            self.last_apple_action = now
            self.apple_thread = threading.Thread(target=self._apple_loop, daemon=True)
            self.apple_thread.start()
            logger.info("Launched Apple Music automation thread")
            time.sleep(5)

        if self.amazon_controller:
            # Add 4 extra minutes to Amazon iso start
            self.next_iso_amazon = now + self.get_isoclipboard_delay("amazon") + 240
            self.last_amazon_action = now
            self.amazon_thread = threading.Thread(target=self._amazon_loop, daemon=True)
            self.amazon_thread.start()
            logger.info("Launched Amazon Music automation thread")

        logger.info("All requested automation threads started")
        return True

    def stop_automation(self):
        """Stop all automation and join the threads."""
        if not self.running:
            logger.warning("No automation is currently running to stop.")
            return

        logger.info("Stopping automation...")
        self.running = False

        # Join each thread if alive
        if self.youtube_thread and self.youtube_thread.is_alive():
            self.youtube_thread.join(timeout=5)
            self.youtube_thread = None

        if self.apple_thread and self.apple_thread.is_alive():
            self.apple_thread.join(timeout=5)
            self.apple_thread = None

        if self.amazon_thread and self.amazon_thread.is_alive():
            self.amazon_thread.join(timeout=5)
            self.amazon_thread = None

        # Reset everything
        with self.action_lock:
            self.next_iso_youtube = 0
            self.next_iso_apple = 0
            self.next_iso_amazon = 0
            self.last_youtube_action = 0
            self.last_apple_action = 0
            self.last_amazon_action = 0

        logger.info("Automation stopped successfully.")

    def start_youtube_only(self) -> bool:
        """Start just YouTube Music automation."""
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
        """Start just Apple Music automation."""
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
        """Start just Amazon Music automation."""
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
        """Pause running automation by setting a flag. Loops will sleep if paused."""
        try:
            with self.action_lock:
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
        """Resume from paused state."""
        try:
            with self.action_lock:
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
        """Get a dictionary describing current automation status."""
        with self.action_lock:
            status = {
                "running": self.running,
                "paused": self.paused,
                "active_apps": []
            }

            if self.youtube_controller:
                status["active_apps"].append("YouTube Music")
                if self.last_youtube_action > 0:
                    status["last_youtube_action"] = time.strftime(
                        '%H:%M:%S',
                        time.localtime(self.last_youtube_action)
                    )
                if self.next_iso_youtube > 0:
                    status["next_youtube_iso"] = time.strftime(
                        '%H:%M:%S',
                        time.localtime(self.next_iso_youtube)
                    )

            if self.apple_controller:
                status["active_apps"].append("Apple Music")
                if self.last_apple_action > 0:
                    status["last_apple_action"] = time.strftime(
                        '%H:%M:%S',
                        time.localtime(self.last_apple_action)
                    )
                if self.next_iso_apple > 0:
                    status["next_apple_iso"] = time.strftime(
                        '%H:%M:%S',
                        time.localtime(self.next_iso_apple)
                    )

            if self.amazon_controller:
                status["active_apps"].append("Amazon Music")
                if self.last_amazon_action > 0:
                    status["last_amazon_action"] = time.strftime(
                        '%H:%M:%S',
                        time.localtime(self.last_amazon_action)
                    )
                if self.next_iso_amazon > 0:
                    status["next_amazon_iso"] = time.strftime(
                        '%H:%M:%S',
                        time.localtime(self.next_iso_amazon)
                    )

            return status