# src/automation/multi_app_scheduler.py
import random
import threading
from queue import Queue, Empty
import time
from typing import Optional, Dict, Tuple, Callable, List, Union
from src.utils.logging_utils import setup_logger
from src.controllers.app_controllers.youtube_music import YouTubeMusicController
from src.controllers.app_controllers.apple_music import AppleMusicController
from src.controllers.app_controllers.amazon_music import AmazonMusicController
from src.controllers.app_controllers.tidal_music import TidalMusicController
from src.controllers.app_controllers.beatport_music import BeatportMusicController
from src.controllers.mutex_mixin import MutexMixin, with_device_lock

logger = setup_logger(__name__)


class MultiMusicAutomation(MutexMixin):
    def __init__(
            self,
            youtube_controller: Optional[YouTubeMusicController] = None,
            apple_controller: Optional[AppleMusicController] = None,
            amazon_controller: Optional[AmazonMusicController] = None,
            tidal_controller: Optional[TidalMusicController] = None,
            beatport_controller: Optional[BeatportMusicController] = None
    ):
        super().__init__()  # Initialize MutexMixin
        self.youtube_controller = youtube_controller
        self.apple_controller = apple_controller
        self.amazon_controller = amazon_controller
        self.tidal_controller = tidal_controller
        self.beatport_controller = beatport_controller
        self.running = False
        self.paused = False
        # Add action queue
        self.action_queue = Queue()
        self.action_lock = threading.Lock()
        self.action_thread = None
        # Thread storage
        self.youtube_thread: Optional[threading.Thread] = None
        self.apple_thread: Optional[threading.Thread] = None
        self.amazon_thread: Optional[threading.Thread] = None
        self.tidal_thread: Optional[threading.Thread] = None
        self.beatport_thread: Optional[threading.Thread] = None
        # Timestamps
        self.next_iso_youtube = 0.0
        self.next_iso_apple = 0.0
        self.next_iso_amazon = 0.0
        self.next_iso_tidal = 0.0
        self.next_beatport_check = 0.0
        self.last_youtube_action = 0.0
        self.last_apple_action = 0.0
        self.last_amazon_action = 0.0
        self.last_tidal_action = 0.0
        self.last_beatport_action = 0.0

    def _process_actions(self):
        """Process queued actions sequentially."""
        while self.running:
            try:
                if self.paused:
                    time.sleep(1)
                    continue
                try:
                    action = self.action_queue.get(timeout=1)
                except Empty:
                    continue
                if action:
                    app_name, func, action_name = action
                    with self.action_lock:
                        logger.info(f"Processing {app_name} {action_name}")
                        if func():
                            logger.info(f"{app_name} {action_name} successful")
                            now = time.time()
                            # Update last action timestamp and minimize the app after success
                            if app_name == 'youtube_music':
                                self.last_youtube_action = now
                                self.youtube_controller.device.press("home")
                            elif app_name == 'apple_music':
                                self.last_apple_action = now
                                self.apple_controller.device.press("home")
                            elif app_name == 'amazon_music':
                                self.last_amazon_action = now
                                self.amazon_controller.device.press("home")
                            elif app_name == 'tidal_music':
                                self.last_tidal_action = now
                                self.tidal_controller.device.press("home")
                            elif app_name == 'beatport':
                                self.last_beatport_action = now
                                self.beatport_controller.device.press("home")
                            time.sleep(random.randint(20, 30))
                        else:
                            logger.error(f"{app_name} {action_name} failed")
                            time.sleep(5)
                    self.action_queue.task_done()
            except Exception as e:
                logger.error(f"Error processing action: {e}")
                time.sleep(1)

    def _get_action_cluster(self,
                            controller: Union[YouTubeMusicController, AppleMusicController,
                            AmazonMusicController, TidalMusicController, BeatportMusicController],
                            app_type: str) -> List[Tuple[Callable, str]]:
        """Generate a human-like cluster of 1-4 actions, with special handling for YouTube Music."""
        actions = []

        # Special case for YouTube Music and Amazon Music - no playback control actions at all
        if app_type == "youtube" or app_type == "amazon":
            # Return an empty list - no actions to perform for these services
            # They will only handle IsoClipboard actions
            return []

        # For all other apps, use the original weighted actions logic
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
            "amazon": (20, 25),
            "tidal": (24, 34)
        }
        base_min, base_max = base_delays[app_type]
        actual_min = max(base_min - random.randint(0, 3), 5)
        actual_max = base_max + random.randint(0, 5)
        minutes = random.randint(actual_min, actual_max)
        seconds = random.randint(0, 59)
        total_seconds = minutes * 60 + seconds
        next_time = time.strftime('%H:%M:%S', time.localtime(time.time() + total_seconds))
        app_name = {
            "youtube": "YouTube Music",
            "apple": "Apple Music",
            "amazon": "Amazon Music",
            "tidal": "Tidal Music"
        }[app_type]
        logger.info(f"Next {app_name} IsoClipboard in {minutes}m {seconds}s (at {next_time})")
        return total_seconds

    def get_music_action_delay(self, app_type: str) -> int:
        delay_configs = {
            "youtube": (0, 6, 45),
            "apple": (1, 7, 42),
            "amazon": (0, 5, 50),
            "tidal": (1, 6, 48),
            "beatport": (1, 5, 45)  # Similar delay pattern to other apps
        }
        min_minutes, max_minutes, min_seconds = delay_configs[app_type]
        minutes = random.randint(min_minutes, max_minutes)
        seconds = random.randint(min_seconds, 59) if minutes == 0 else random.randint(0, 59)
        app_name = {
            "youtube": "YouTube Music",
            "apple": "Apple Music",
            "amazon": "Amazon Music",
            "tidal": "Tidal Music",
            "beatport": "Beatport"
        }[app_type]
        total_seconds = minutes * 60 + seconds
        next_time = time.strftime('%H:%M:%S', time.localtime(time.time() + total_seconds))
        logger.info(f"Next {app_name} action in {minutes}m {seconds}s (at {next_time})")
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
        if self.tidal_controller:
            last_actions.append(self.last_tidal_action)
        if self.beatport_controller:
            last_actions.append(self.last_beatport_action)
        if last_actions:
            most_recent = max(last_actions)
            return (now - most_recent) >= 10
        return True

    @with_device_lock
    def _add_action(self, app_name: str, func: Callable, action_name: str):
        """Add action to queue."""
        try:
            self.action_queue.put((app_name, func, action_name))
            logger.debug(f"Queued {app_name} {action_name}")
        except Exception as e:
            logger.error(f"Error adding action to queue: {e}")
            return False
        return True

    def _youtube_loop(self):
        """YouTube loop focused only on IsoClipboard actions."""
        while self.running and self.youtube_controller:
            try:
                if self.paused:
                    time.sleep(300)
                    continue
                now = time.time()
                # Handle IsoClipboard if it's time
                if now >= self.next_iso_youtube:
                    self._add_action(
                        'youtube_music',
                        self.youtube_controller.handle_isoclipboard,
                        'IsoClipboard'
                    )
                    self.action_queue.join()
                    self.next_iso_youtube = time.time() + self.get_isoclipboard_delay("youtube")
                    continue

                # Skip all monitoring logs since we're not taking any actions
                # Just sleep for a reasonable time before checking IsoClipboard again
                seconds_until_next_iso = max(0, self.next_iso_youtube - time.time())
                sleep_time = min(30, seconds_until_next_iso)
                time.sleep(sleep_time)

                # Check if it's safe to perform a new cluster of actions
                # if self._check_safe_to_act():
                #     actions = self._get_action_cluster(self.youtube_controller, "youtube")
                #     total_steps = len(actions)
                #     for i, (func, action_name) in enumerate(actions):
                #         if i > 0:
                #             intra_cluster_delay = self._get_human_delay(is_cluster=True)
                #             time.sleep(intra_cluster_delay)
                #         logger.info(f"Processing YouTube Music action {i + 1}/{total_steps}: {action_name}")
                #         self._add_action('youtube_music', func, action_name)
                #         self.action_queue.join()
                # # Use the custom delay function to determine the wait time before the next cluster
                # delay = self.get_music_action_delay("youtube")
                # time.sleep(delay)
            except Exception as e:
                logger.error(f"Error in YouTube loop: {e}")
                time.sleep(60)

    def _tidal_loop(self):
        """Tidal Music loop using action queue with numeric logging for each human-like step."""
        while self.running and self.tidal_controller:
            try:
                if self.paused:
                    time.sleep(300)
                    continue
                now = time.time()
                # Handle IsoClipboard if it's time
                if now >= self.next_iso_tidal:
                    self._add_action(
                        'tidal_music',
                        self.tidal_controller.handle_isoclipboard,
                        'IsoClipboard'
                    )
                    self.action_queue.join()
                    self.next_iso_tidal = time.time() + self.get_isoclipboard_delay("tidal")
                    continue
                # Check if it's safe to perform a new cluster of actions
                if self._check_safe_to_act():
                    actions = self._get_action_cluster(self.tidal_controller, "tidal")
                    total_steps = len(actions)
                    for i, (func, action_name) in enumerate(actions):
                        if i > 0:
                            intra_cluster_delay = self._get_human_delay(is_cluster=True)
                            time.sleep(intra_cluster_delay)
                        logger.info(f"Processing Tidal Music action {i + 1}/{total_steps}: {action_name}")
                        self._add_action('tidal_music', func, action_name)
                        self.action_queue.join()
                # Use the custom delay function to determine the wait time before the next cluster
                delay = self.get_music_action_delay("tidal")
                time.sleep(delay)
            except Exception as e:
                logger.error(f"Error in Tidal loop: {e}")
                time.sleep(60)

    def _beatport_loop(self):
        """Beatport loop with improved monitoring and recovery."""
        while self.running and self.beatport_controller:
            try:
                if self.paused:
                    time.sleep(300)
                    continue

                now = time.time()

                # Check daily limit first with forced update
                if self.beatport_controller.check_daily_limit_reached(force_check=True):
                    logger.warning("Beatport daily limit reached in main loop check")
                    # If playing, force stop
                    if self.beatport_controller.is_playing:
                        self.beatport_controller._safe_force_stop()
                    # Wait a while before checking again
                    time.sleep(900)  # 15 minutes
                    continue

                # If not playing but should be, start fresh
                if not self.beatport_controller.is_playing:
                    logger.info("Beatport not playing - initiating setup")
                    self._add_action(
                        'beatport',
                        self.beatport_controller.handle_initial_setup,
                        'Initial Setup'
                    )
                    self.action_queue.join()
                    # Wait a while before next action
                    time.sleep(random.randint(180, 300))  # 3-5 minutes
                    continue

                # Only do actions at reasonable intervals if we're playing
                # Check if it's safe to perform a new cluster of actions
                if self._check_safe_to_act():
                    actions = self._get_action_cluster(self.beatport_controller, "beatport")
                    total_steps = len(actions)
                    for i, (func, action_name) in enumerate(actions):
                        if i > 0:
                            intra_cluster_delay = self._get_human_delay(is_cluster=True)
                            time.sleep(intra_cluster_delay)
                        logger.info(f"Processing Beatport action {i + 1}/{total_steps}: {action_name}")
                        self._add_action('beatport', func, action_name)
                        self.action_queue.join()

                        # Check limit after each action
                        if self.beatport_controller.check_daily_limit_reached():
                            logger.warning("Daily limit reached after action")
                            break

                # Use custom delay
                delay = self.get_music_action_delay("beatport")
                time.sleep(delay)
            except Exception as e:
                logger.error(f"Error in Beatport loop: {e}")
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
            # Wait for playback to start before minimizing
            logger.info("Waiting for playback to start...")
            time.sleep(8)
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

    @with_device_lock
    def _tidal_initial_setup(self) -> bool:
        """Initial setup needs device lock as it's preparing the device state."""
        logger.info("Starting Tidal Music initial setup...")
        try:
            if not self.tidal_controller.force_stop():
                logger.warning("Failed to close Tidal Music")
            time.sleep(2)
            if not self.tidal_controller.handle_isoclipboard():
                logger.error("Tidal Music iso-clipboard setup failed")
                return False
            # Wait for playback to start before minimizing
            logger.info("Waiting for playback to start...")
            time.sleep(8)
            if not self.tidal_controller.manage_window_state(True):
                logger.warning("Failed to minimize Tidal Music window")
            logger.info("Tidal Music initial setup completed")
            return True
        except Exception as e:
            logger.error(f"Error in Tidal init setup: {e}")
            return False

    @with_device_lock
    def _beatport_initial_setup(self) -> bool:
        """Initial setup for Beatport with daily limit check."""
        logger.info("Starting Beatport initial setup...")
        try:
            # Check if daily limit is already reached
            if self.beatport_controller.check_daily_limit_reached():
                logger.warning("Beatport daily limit already reached, continue setup")
            
                # FIXME: What was the reason to skip all setups if daily limit is reached?
                #  It makes no sense, because it caused False for wholeinitial setup process.
                #  But we check daily limits in loop and show continue run beatport once daily limit is refereshed
                # so seems we need intialize everything, and in beatport loop actual activity is skipped. At least I hope so.

                # FIXME: we can't just continue here because further handle_initial_setup() again checks limits and returns False.
                # All this at the end causes fail all apps start. SO we skip intiialization right now and hope it continue working
                # in main loop after daily limit is refreshed. handle_initial_setup() is called in main loop again ;)))) 

                # FIXME: duplicates, every where!
                return True

            # Force stop Beatport if running
            if not self.beatport_controller.force_stop():
                logger.warning("Failed to close Beatport")

            time.sleep(2)

            # Run initial setup
            if not self.beatport_controller.handle_initial_setup():
                logger.error("Beatport initial setup failed")
                return False

            # Wait for playback to start before minimizing
            logger.info("Waiting for playback to start...")
            time.sleep(8)
            
            # Minimize window
            if not self.beatport_controller.manage_window_state(True):
                logger.warning("Failed to minimize Beatport window")

            logger.info("Beatport initial setup completed")
            return True
        except Exception as e:
            logger.error(f"Error in Beatport init setup: {e}")
            return False

    def start_automation(self) -> bool:
        """Start automation for all available controllers."""
        if self.running:
            logger.warning("Automation already running")
            return False
        controllers_available = any([
            self.youtube_controller,
            self.apple_controller,
            self.amazon_controller,
            self.tidal_controller,
            self.beatport_controller
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
        if self.tidal_controller and not self._tidal_initial_setup():
            return False
        if self.beatport_controller and not self._beatport_initial_setup():
            return False
        # Set running flag before starting threads
        self.running = True
        now = time.time()
        # Start action processing thread first
        self.action_thread = threading.Thread(target=self._process_actions, daemon=True)
        self.action_thread.start()
        logger.info("Started action processing thread")
        # Then start individual app threads
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
        if self.tidal_controller:
            self.next_iso_tidal = now + self.get_isoclipboard_delay("tidal")
            self.last_tidal_action = now
            self.tidal_thread = threading.Thread(target=self._tidal_loop, daemon=True)
            self.tidal_thread.start()
            logger.info("Launched Tidal Music automation thread")
        if self.beatport_controller:
            self.next_beatport_check = now + random.randint(60, 180)  # Start in 1-3 minutes
            self.last_beatport_action = now
            self.beatport_thread = threading.Thread(target=self._beatport_loop, daemon=True)
            self.beatport_thread.start()
            logger.info("Launched Beatport automation thread")
        logger.info("All requested automation threads started")
        return True

    def stop_automation(self):
        """Stop automation for all running controllers."""
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
        if self.tidal_thread and self.tidal_thread.is_alive():
            self.tidal_thread.join(timeout=5)
            self.tidal_thread = None
        if self.beatport_thread and self.beatport_thread.is_alive():
            self.beatport_thread.join(timeout=5)
            self.beatport_thread = None
        # Reset all timestamps
        self.next_iso_youtube = 0
        self.next_iso_apple = 0
        self.next_iso_amazon = 0
        self.next_iso_tidal = 0
        self.next_beatport_check = 0
        self.last_youtube_action = 0
        self.last_apple_action = 0
        self.last_amazon_action = 0
        self.last_tidal_action = 0
        self.last_beatport_action = 0
        logger.info("Automation stopped successfully.")

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
        if self.tidal_controller:
            status["active_apps"].append("Tidal Music")
            if self.last_tidal_action > 0:
                status["last_tidal_action"] = time.strftime('%H:%M:%S',
                                                            time.localtime(self.last_tidal_action))
            if self.next_iso_tidal > 0:
                status["next_tidal_iso"] = time.strftime('%H:%M:%S',
                                                         time.localtime(self.next_iso_tidal))
        if self.beatport_controller:
            status["active_apps"].append("Beatport")
            if self.last_beatport_action > 0:
                status["last_beatport_action"] = time.strftime('%H:%M:%S',
                                                               time.localtime(self.last_beatport_action))
            if self.next_beatport_check > 0:
                status["next_beatport_check"] = time.strftime('%H:%M:%S',
                                                              time.localtime(self.next_beatport_check))
            # Add Beatport-specific daily limit info
            if self.beatport_controller:
                hours_played = self.beatport_controller.daily_playtime_seconds / 3600
                hours_remaining = self.beatport_controller.daily_limit_hours - hours_played

                status["beatport_hours_played"] = round(hours_played, 2)
                status["beatport_hours_remaining"] = round(max(0, hours_remaining), 2)
                status["beatport_daily_limit"] = self.beatport_controller.daily_limit_hours
                status["beatport_limit_reached"] = hours_remaining <= 0

        return status

    def _apple_loop(self):
        """Apple Music loop using action queue with numeric logging for each human-like step."""
        while self.running and self.apple_controller:
            try:
                if self.paused:
                    time.sleep(300)
                    continue
                now = time.time()
                # Handle IsoClipboard if it's time
                if now >= self.next_iso_apple:
                    self._add_action(
                        'apple_music',
                        self.apple_controller.handle_isoclipboard,
                        'IsoClipboard'
                    )
                    self.action_queue.join()
                    self.next_iso_apple = now + self.get_isoclipboard_delay("apple")
                    continue
                # Check if it's safe to perform a new cluster of actions
                if self._check_safe_to_act():
                    actions = self._get_action_cluster(self.apple_controller, "apple")
                    total_steps = len(actions)
                    for i, (func, action_name) in enumerate(actions):
                        if i > 0:
                            intra_cluster_delay = self._get_human_delay(is_cluster=True)
                            time.sleep(intra_cluster_delay)
                        logger.info(f"Processing Apple Music action {i + 1}/{total_steps}: {action_name}")
                        self._add_action('apple_music', func, action_name)
                        self.action_queue.join()
                # Use the custom delay function to determine the wait time before the next cluster
                delay = self.get_music_action_delay("apple")
                time.sleep(delay)
            except Exception as e:
                logger.error(f"Error in Apple loop: {e}")
                time.sleep(60)

    def _amazon_loop(self):
        """Amazon Music loop focused only on IsoClipboard actions."""
        while self.running and self.amazon_controller:
            try:
                if self.paused:
                    time.sleep(300)
                    continue

                now = time.time()
                # Handle IsoClipboard if it's time
                if now >= self.next_iso_amazon:
                    self._add_action(
                        'amazon_music',
                        self.amazon_controller.handle_isoclipboard,
                        'IsoClipboard'
                    )
                    self.action_queue.join()
                    self.next_iso_amazon = time.time() + self.get_isoclipboard_delay("amazon")
                    continue

                # Just sleep for a reasonable time before checking IsoClipboard again
                seconds_until_next_iso = max(0, self.next_iso_amazon - time.time())
                sleep_time = min(30, seconds_until_next_iso)
                time.sleep(sleep_time)

                # Check if it's safe to perform a new cluster of actions
                # if self._check_safe_to_act():
                #     actions = self._get_action_cluster(self.amazon_controller, "amazon")
                #     total_steps = len(actions)
                #     for i, (func, action_name) in enumerate(actions):
                #         if i > 0:
                #             intra_cluster_delay = self._get_human_delay(is_cluster=True)
                #             time.sleep(intra_cluster_delay)
                #         logger.info(f"Processing Amazon Music action {i + 1}/{total_steps}: {action_name}")
                #         self._add_action('amazon_music', func, action_name)
                #         self.action_queue.join()

            except Exception as e:
                logger.error(f"Error in Amazon loop: {e}")
                time.sleep(60)

    def start_tidal_only(self) -> bool:
        """Start Tidal Music automation only with initial setup."""
        if not self.tidal_controller:
            logger.error("No Tidal Music controller available")
            return False

        # Run initial setup for Tidal Music
        if not self._tidal_initial_setup():
            logger.error("Tidal Music initial setup failed")
            return False

        self.running = True
        now = time.time()

        # Start action processing thread
        self.action_thread = threading.Thread(target=self._process_actions, daemon=True)
        self.action_thread.start()

        # Set delays and start the Tidal thread
        self.next_iso_tidal = now + self.get_isoclipboard_delay("tidal")
        self.last_tidal_action = now
        self.tidal_thread = threading.Thread(target=self._tidal_loop, daemon=True)
        self.tidal_thread.start()

        logger.info("Started Tidal Music automation")
        return True

    def start_beatport_only(self) -> bool:
        """Start Beatport automation only."""
        if not self.beatport_controller:
            logger.error("No Beatport controller available")
            return False

        self.running = True
        now = time.time()

        # Start action processing thread
        self.action_thread = threading.Thread(target=self._process_actions, daemon=True)
        self.action_thread.start()

        # Set check delay and start Beatport thread only
        self.next_beatport_check = now + random.randint(60, 180)  # Start in 1-3 minutes
        self.last_beatport_action = now
        self.beatport_thread = threading.Thread(target=self._beatport_loop, daemon=True)
        self.beatport_thread.start()

        logger.info("Started Beatport automation only")
        return True

    def start_youtube_only(self) -> bool:
        """Start YouTube Music automation only with initial setup."""
        if not self.youtube_controller:
            logger.error("No YouTube Music controller available")
            return False

        # Run initial setup for YouTube Music
        if not self._youtube_initial_setup():
            logger.error("YouTube Music initial setup failed")
            return False

        self.running = True
        now = time.time()

        # Start action processing thread
        self.action_thread = threading.Thread(target=self._process_actions, daemon=True)
        self.action_thread.start()

        # Set delays and start the YouTube thread
        self.next_iso_youtube = now + self.get_isoclipboard_delay("youtube")
        self.last_youtube_action = now
        self.youtube_thread = threading.Thread(target=self._youtube_loop, daemon=True)
        self.youtube_thread.start()
        logger.info("Started YouTube Music automation")
        return True

    def start_amazon_only(self) -> bool:
        """Start Amazon Music automation only with initial setup."""
        if not self.amazon_controller:
            logger.error("No Amazon Music controller available")
            return False

        # Run initial setup for Amazon Music
        if not self._amazon_initial_setup():
            logger.error("Amazon Music initial setup failed")
            return False

        self.running = True
        now = time.time()

        # Start action processing thread
        self.action_thread = threading.Thread(target=self._process_actions, daemon=True)
        self.action_thread.start()

        # Set delays and start the Amazon thread
        self.next_iso_amazon = now + self.get_isoclipboard_delay("amazon")
        self.last_amazon_action = now
        self.amazon_thread = threading.Thread(target=self._amazon_loop, daemon=True)
        self.amazon_thread.start()
        logger.info("Started Amazon Music automation")
        return True

    def start_apple_only(self) -> bool:
        """Start Apple Music automation only with initial setup."""
        if not self.apple_controller:
            logger.error("No Apple Music controller available")
            return False

        # Run initial setup for Apple Music
        if not self._apple_initial_setup():
            logger.error("Apple Music initial setup failed")
            return False

        self.running = True
        now = time.time()

        # Start action processing thread
        self.action_thread = threading.Thread(target=self._process_actions, daemon=True)
        self.action_thread.start()

        # Set delays and start the Apple thread
        self.next_iso_apple = now + self.get_isoclipboard_delay("apple")
        self.last_apple_action = now
        self.apple_thread = threading.Thread(target=self._apple_loop, daemon=True)
        self.apple_thread.start()
        logger.info("Started Apple Music automation")
        return True