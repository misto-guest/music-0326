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
        beatport_controller: Optional[BeatportMusicController] = None,
        primary_user_id: int = 0,
        secondary_user_id: Optional[int] = None,
        apple_user_ids: Optional[List[int]] = None,
        tidal_user_ids: Optional[List[int]] = None,
        beatport_user_ids: Optional[List[int]] = None,
    ):
        super().__init__()
        self.youtube_controller = youtube_controller
        self.apple_controller = apple_controller
        self.amazon_controller = amazon_controller
        self.tidal_controller = tidal_controller
        self.beatport_controller = beatport_controller

        self.running = False
        self.paused = False

        # Multi-user support for these apps (provided by caller)
        self.primary_user_id = primary_user_id
        self.secondary_user_id = secondary_user_id

        base_user_ids: List[int] = [primary_user_id]
        if secondary_user_id is not None and secondary_user_id != primary_user_id:
            base_user_ids.append(secondary_user_id)

        # Per-app user lists (allow empty lists to disable per-user automation)
        self.apple_user_ids: List[int] = base_user_ids if apple_user_ids is None else list(apple_user_ids)
        self.tidal_user_ids: List[int] = base_user_ids if tidal_user_ids is None else list(tidal_user_ids)
        self.beatport_user_ids: List[int] = base_user_ids if beatport_user_ids is None else list(beatport_user_ids)

        # Action queue + worker
        self.action_queue: Queue = Queue()
        self.action_lock = threading.Lock()
        self.action_thread: Optional[threading.Thread] = None

        # Threads
        self.youtube_thread: Optional[threading.Thread] = None
        self.amazon_thread: Optional[threading.Thread] = None

        # Per-user threads for Apple / Tidal / Beatport
        self.apple_threads: Dict[int, Optional[threading.Thread]] = {
            uid: None for uid in self.apple_user_ids
        }
        self.tidal_threads: Dict[int, Optional[threading.Thread]] = {
            uid: None for uid in self.tidal_user_ids
        }
        self.beatport_threads: Dict[int, Optional[threading.Thread]] = {
            uid: None for uid in self.beatport_user_ids
        }

        # Timestamps (coarse per-app, not per-user; good enough for safe-guarding)
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

    # -------------------------------------------------------------------------
    # User/profile configuration (Apple / Tidal / Beatport)
    # -------------------------------------------------------------------------
    def configure_users(
        self,
        *,
        primary_user_id: Optional[int] = None,
        secondary_user_id: Optional[int] = None,
        apple_user_ids: Optional[List[int]] = None,
        tidal_user_ids: Optional[List[int]] = None,
        beatport_user_ids: Optional[List[int]] = None,
    ) -> None:
        """
        Configure which Android user IDs to use for per-user automation threads.

        Intended to be called by the CLI layer BEFORE starting automation.
        No adb detection happens here.
        """
        if self.running:
            logger.warning("Cannot reconfigure user IDs while automation is running")
            return

        if primary_user_id is not None:
            self.primary_user_id = primary_user_id
        if secondary_user_id is not None or self.secondary_user_id is None:
            # allow explicit None to clear, but only if caller passes it
            self.secondary_user_id = secondary_user_id

        base_user_ids: List[int] = [self.primary_user_id]
        if self.secondary_user_id is not None and self.secondary_user_id != self.primary_user_id:
            base_user_ids.append(self.secondary_user_id)

        if apple_user_ids is None:
            self.apple_user_ids = list(base_user_ids)
        else:
            self.apple_user_ids = list(apple_user_ids)

        if tidal_user_ids is None:
            self.tidal_user_ids = list(base_user_ids)
        else:
            self.tidal_user_ids = list(tidal_user_ids)

        if beatport_user_ids is None:
            self.beatport_user_ids = list(base_user_ids)
        else:
            self.beatport_user_ids = list(beatport_user_ids)

        # Rebuild per-user thread maps to match configured user IDs
        self.apple_threads = {uid: None for uid in self.apple_user_ids}
        self.tidal_threads = {uid: None for uid in self.tidal_user_ids}
        self.beatport_threads = {uid: None for uid in self.beatport_user_ids}

    # -------------------------------------------------------------------------
    # Action queue worker
    # -------------------------------------------------------------------------
    def _process_actions(self):
        """Process queued actions sequentially."""
        while self.running:
            try:
                if self.paused:
                    time.sleep(1)
                    continue

                try:
                    app_name, func, action_name = self.action_queue.get(timeout=1)
                except Empty:
                    continue

                if not func:
                    self.action_queue.task_done()
                    continue

                with self.action_lock:
                    logger.info(f"Processing {app_name}: {action_name}")
                    success = False
                    try:
                        success = func()
                    except Exception as e:
                        logger.error(f"Error executing {app_name} action {action_name}: {e}")

                    if success:
                        logger.info(f"{app_name}: {action_name} successful")
                        now = time.time()
                        if app_name == "youtube_music":
                            self.last_youtube_action = now
                            self.youtube_controller.device.press("home")
                        elif app_name == "apple_music":
                            self.last_apple_action = now
                            self.apple_controller.device.press("home")
                        elif app_name == "amazon_music":
                            self.last_amazon_action = now
                            self.amazon_controller.device.press("home")
                        elif app_name == "tidal_music":
                            self.last_tidal_action = now
                            self.tidal_controller.device.press("home")
                        elif app_name == "beatport":
                            self.last_beatport_action = now
                            self.beatport_controller.device.press("home")
                        # small randomized delay between clusters
                        time.sleep(random.randint(20, 30))
                    else:
                        logger.error(f"{app_name}: {action_name} failed")
                        time.sleep(5)

                self.action_queue.task_done()
            except Exception as e:
                logger.error(f"Error in action processor: {e}")
                time.sleep(1)

    # -------------------------------------------------------------------------
    # Cluster & delay logic
    # -------------------------------------------------------------------------
    def _get_action_cluster(
        self,
        controller: Union[
            YouTubeMusicController,
            AppleMusicController,
            AmazonMusicController,
            TidalMusicController,
            BeatportMusicController,
        ],
        app_type: str,
        user_id: Optional[int] = None,
    ) -> List[Tuple[Callable, str]]:
        """
        Generate a human-like cluster of 1–4 actions.

        For YouTube & Amazon, we skip playback actions entirely.
        For Apple/Tidal/Beatport, we pass user_id where needed.
        """
        actions: List[Tuple[Callable, str]] = []

        # YouTube & Amazon: no playback clusters, only IsoClipboard in loops
        if app_type in ("youtube", "amazon"):
            return []

        # Build weighted actions per app
        if app_type == "apple":
            if user_id is None:
                raise ValueError("user_id is required for Apple actions")
            weighted_actions = [
                (lambda uid=user_id: controller.next_track(uid), "Next track", 50),
                (lambda uid=user_id: controller.previous_track(uid), "Previous track", 20),
                (lambda uid=user_id: controller.like_current_song(uid), "Like song", 30),
            ]
        elif app_type == "tidal":
            if user_id is None:
                raise ValueError("user_id is required for Tidal actions")
            weighted_actions = [
                (lambda uid=user_id: controller.next_track(uid), "Next track", 50),
                (lambda uid=user_id: controller.previous_track(uid), "Previous track", 20),
                (lambda uid=user_id: controller.like_current_song(uid), "Like song", 30),
            ]
        elif app_type == "beatport":
            if user_id is None:
                raise ValueError("user_id is required for Beatport actions")
            weighted_actions = [
                (lambda uid=user_id: controller.next_track(uid), "Next track", 50),
                (lambda uid=user_id: controller.previous_track(uid), "Previous track", 20),
                # like_current_song has no user_id argument in Beatport
                (controller.like_current_song, "Like song", 30),
            ]
        else:
            # fallback (shouldn't really be used)
            weighted_actions = [
                (controller.next_track, "Next track", 50),
                (controller.previous_track, "Previous track", 20),
                (controller.like_current_song, "Like song", 30),
            ]

        cluster_weights: Dict[int, int] = {
            1: 45,
            2: 30,
            3: 15,
            4: 10,
        }
        cluster_size = random.choices(
            list(cluster_weights.keys()),
            weights=list(cluster_weights.values()),
        )[0]

        for _ in range(cluster_size):
            action = random.choices(
                weighted_actions,
                weights=[w[2] for w in weighted_actions],
            )[0]
            actions.append((action[0], action[1]))
            if action[1] == "Like song":
                # after like, bias harder towards next track
                weighted_actions[0] = (weighted_actions[0][0], weighted_actions[0][1], 80)

        return actions

    def _get_human_delay(self, is_cluster: bool = False) -> int:
        if is_cluster:
            return random.randint(2, 8)

        # (min, max, weight)
        weights = [
            (60, 180, 40),   # 1–3 min
            (181, 300, 30),  # 3–5 min
            (301, 480, 20),  # 5–8 min
            (481, 720, 10),  # 8–12 min
        ]
        selected = random.choices(weights, weights=[w[2] for w in weights])[0]
        return random.randint(selected[0], selected[1])

    def get_isoclipboard_delay(self, app_type: str) -> int:
        base_delays = {
            "youtube": (22, 33),
            "apple": (25, 35),
            "amazon": (20, 25),
            "tidal": (24, 34),
        }
        base_min, base_max = base_delays[app_type]
        actual_min = max(base_min - random.randint(0, 3), 5)
        actual_max = base_max + random.randint(0, 5)
        minutes = random.randint(actual_min, actual_max)
        seconds = random.randint(0, 59)
        total_seconds = minutes * 60 + seconds
        next_time = time.strftime("%H:%M:%S", time.localtime(time.time() + total_seconds))
        app_name = {
            "youtube": "YouTube Music",
            "apple": "Apple Music",
            "amazon": "Amazon Music",
            "tidal": "Tidal Music",
        }[app_type]
        logger.info(f"Next {app_name} IsoClipboard in {minutes}m {seconds}s (at {next_time})")
        return total_seconds

    def get_music_action_delay(self, app_type: str) -> int:
        delay_configs = {
            "youtube": (0, 6, 45),
            "apple": (1, 7, 42),
            "amazon": (0, 5, 50),
            "tidal": (1, 6, 48),
            "beatport": (1, 5, 45),
        }
        min_minutes, max_minutes, min_seconds = delay_configs[app_type]
        minutes = random.randint(min_minutes, max_minutes)
        seconds = random.randint(min_seconds, 59) if minutes == 0 else random.randint(0, 59)
        app_name = {
            "youtube": "YouTube Music",
            "apple": "Apple Music",
            "amazon": "Amazon Music",
            "tidal": "Tidal Music",
            "beatport": "Beatport",
        }[app_type]
        total_seconds = minutes * 60 + seconds
        next_time = time.strftime("%H:%M:%S", time.localtime(time.time() + total_seconds))
        logger.info(f"Next {app_name} action in {minutes}m {seconds}s (at {next_time})")
        return total_seconds

    # -------------------------------------------------------------------------
    # Safety checks & queue add
    # -------------------------------------------------------------------------
    @with_device_lock
    def _check_safe_to_act(self) -> bool:
        """Check if enough time has passed since the last action on any app."""
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
            return (now - most_recent) >= 10.0  # at least 10 seconds gap
        return True

    @with_device_lock
    def _add_action(self, app_name: str, func: Callable, action_name: str) -> bool:
        """Enqueue an action."""
        try:
            self.action_queue.put((app_name, func, action_name))
            logger.debug(f"Queued {app_name}: {action_name}")
            return True
        except Exception as e:
            logger.error(f"Error queuing {app_name} action {action_name}: {e}")
            return False

    # -------------------------------------------------------------------------
    # YouTube & Amazon loops (unchanged behavior)
    # -------------------------------------------------------------------------
    def _youtube_loop(self):
        """YouTube loop focused only on IsoClipboard actions."""
        while self.running and self.youtube_controller:
            try:
                if self.paused:
                    time.sleep(300)
                    continue

                now = time.time()
                if now >= self.next_iso_youtube:
                    self._add_action(
                        "youtube_music",
                        self.youtube_controller.handle_isoclipboard,
                        "IsoClipboard",
                    )
                    self.action_queue.join()
                    self.next_iso_youtube = time.time() + self.get_isoclipboard_delay("youtube")
                    continue

                seconds_until_next_iso = max(0, self.next_iso_youtube - time.time())
                sleep_time = min(30, seconds_until_next_iso)
                time.sleep(sleep_time)
            except Exception as e:
                logger.error(f"Error in YouTube loop: {e}")
                time.sleep(60)

    def _amazon_loop(self):
        """Amazon Music loop focused only on IsoClipboard actions."""
        while self.running and self.amazon_controller:
            try:
                if self.paused:
                    time.sleep(300)
                    continue

                now = time.time()
                if now >= self.next_iso_amazon:
                    self._add_action(
                        "amazon_music",
                        self.amazon_controller.handle_isoclipboard,
                        "IsoClipboard",
                    )
                    self.action_queue.join()
                    self.next_iso_amazon = time.time() + self.get_isoclipboard_delay("amazon")
                    continue

                seconds_until_next_iso = max(0, self.next_iso_amazon - time.time())
                sleep_time = min(30, seconds_until_next_iso)
                time.sleep(sleep_time)
            except Exception as e:
                logger.error(f"Error in Amazon loop: {e}")
                time.sleep(60)

    # -------------------------------------------------------------------------
    # Apple loops – per-user
    # -------------------------------------------------------------------------
    def _apple_loop_for_user(self, user_id: int):
        """Apple Music loop for a specific user."""
        while self.running and self.apple_controller:
            try:
                if self.paused:
                    time.sleep(300)
                    continue

                now = time.time()

                # Per-app IsoClipboard scheduling (same timer for both users, but that's fine)
                if now >= self.next_iso_apple:
                    self._add_action(
                        "apple_music",
                        lambda uid=user_id: self.apple_controller.handle_isoclipboard(uid),
                        f"IsoClipboard (user {user_id})",
                    )
                    self.action_queue.join()
                    self.next_iso_apple = now + self.get_isoclipboard_delay("apple")
                    continue

                if self._check_safe_to_act():
                    actions = self._get_action_cluster(
                        self.apple_controller, "apple", user_id=user_id
                    )
                    total_steps = len(actions)
                    for i, (func, action_name) in enumerate(actions):
                        if i > 0:
                            time.sleep(self._get_human_delay(is_cluster=True))
                        logger.info(
                            f"Apple Music (user {user_id}) action "
                            f"{i + 1}/{total_steps}: {action_name}"
                        )
                        self._add_action(
                            "apple_music",
                            func,
                            f"{action_name} (user {user_id})",
                        )
                        self.action_queue.join()

                delay = self.get_music_action_delay("apple")
                time.sleep(delay)
            except Exception as e:
                logger.error(f"Error in Apple loop (user {user_id}): {e}")
                time.sleep(60)

    # -------------------------------------------------------------------------
    # Tidal loops – per-user
    # -------------------------------------------------------------------------
    def _tidal_loop_for_user(self, user_id: int):
        """Tidal Music loop for a specific user."""
        while self.running and self.tidal_controller:
            try:
                if self.paused:
                    time.sleep(300)
                    continue

                now = time.time()

                if now >= self.next_iso_tidal:
                    self._add_action(
                        "tidal_music",
                        lambda uid=user_id: self.tidal_controller.handle_isoclipboard(uid),
                        f"IsoClipboard (user {user_id})",
                    )
                    self.action_queue.join()
                    self.next_iso_tidal = now + self.get_isoclipboard_delay("tidal")
                    continue

                if self._check_safe_to_act():
                    actions = self._get_action_cluster(
                        self.tidal_controller, "tidal", user_id=user_id
                    )
                    total_steps = len(actions)
                    for i, (func, action_name) in enumerate(actions):
                        if i > 0:
                            time.sleep(self._get_human_delay(is_cluster=True))
                        logger.info(
                            f"Tidal Music (user {user_id}) action "
                            f"{i + 1}/{total_steps}: {action_name}"
                        )
                        self._add_action(
                            "tidal_music",
                            func,
                            f"{action_name} (user {user_id})",
                        )
                        self.action_queue.join()

                delay = self.get_music_action_delay("tidal")
                time.sleep(delay)
            except Exception as e:
                logger.error(f"Error in Tidal loop (user {user_id}): {e}")
                time.sleep(60)

    # -------------------------------------------------------------------------
    # Beatport loops – per-user
    # -------------------------------------------------------------------------
    def _beatport_loop_for_user(self, user_id: int):
        """Beatport loop for a specific user, with per-user daily limit."""
        while self.running and self.beatport_controller:
            try:
                if self.paused:
                    time.sleep(300)
                    continue

                now = time.time()

                # User-specific daily limit
                if self.beatport_controller.check_daily_limit_reached(
                    user_id=user_id, force_check=True
                ):
                    logger.warning(
                        f"Beatport daily limit reached in loop for user {user_id}"
                    )
                    # If this user is playing, force stop that user's instance
                    if self.beatport_controller.user_is_playing.get(user_id, False):
                        self.beatport_controller._safe_force_stop(user_id)
                    time.sleep(900)  # 15 minutes before re-check
                    continue

                # If this user is not playing, try to set up
                if not self.beatport_controller.user_is_playing.get(user_id, False):
                    logger.info(
                        f"Beatport not playing for user {user_id} - initiating setup"
                    )
                    self._add_action(
                        "beatport",
                        lambda uid=user_id: self.beatport_controller.handle_initial_setup(
                            uid
                        ),
                        f"Initial Setup (user {user_id})",
                    )
                    self.action_queue.join()
                    time.sleep(random.randint(180, 300))  # 3–5 min
                    continue

                # If playing, occasionally perform actions
                if self._check_safe_to_act():
                    actions = self._get_action_cluster(
                        self.beatport_controller, "beatport", user_id=user_id
                    )
                    total_steps = len(actions)
                    for i, (func, action_name) in enumerate(actions):
                        if i > 0:
                            time.sleep(self._get_human_delay(is_cluster=True))
                        logger.info(
                            f"Beatport (user {user_id}) action "
                            f"{i + 1}/{total_steps}: {action_name}"
                        )
                        self._add_action(
                            "beatport",
                            func,
                            f"{action_name} (user {user_id})",
                        )
                        self.action_queue.join()

                        # Re-check limit after each action
                        if self.beatport_controller.check_daily_limit_reached(
                            user_id=user_id
                        ):
                            logger.warning(
                                f"Beatport daily limit reached after action for user {user_id}"
                            )
                            break

                delay = self.get_music_action_delay("beatport")
                time.sleep(delay)
            except Exception as e:
                logger.error(f"Error in Beatport loop (user {user_id}): {e}")
                time.sleep(60)

    # -------------------------------------------------------------------------
    # Initial setups
    # -------------------------------------------------------------------------
    @with_device_lock
    def _youtube_initial_setup(self) -> bool:
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
        """Initial setup for Apple Music for all configured user profiles."""
        logger.info("Starting Apple Music initial setup...")
        try:
            for uid in self.apple_user_ids:
                logger.info(f"Apple Music initial setup for user {uid}...")
                if not self.apple_controller.force_stop(uid):
                    logger.warning(f"Failed to close Apple Music for user {uid}")
                time.sleep(4)
                if not self.apple_controller.handle_isoclipboard(uid):
                    logger.error(
                        f"Apple Music iso-clipboard setup failed for user {uid}"
                    )
                    return False

            # Wait for playback to start before minimizing
            logger.info("Waiting for playback to start...")
            time.sleep(8)
            if not self.apple_controller.manage_window_state(True):
                logger.warning("Failed to minimize Apple Music window")

            logger.info("Apple Music initial setup completed for all users")
            return True
        except Exception as e:
            logger.error(f"Error in Apple init setup: {e}")
            return False

    @with_device_lock
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

    @with_device_lock
    def _tidal_initial_setup(self) -> bool:
        """Initial setup for Tidal Music for all configured user profiles."""
        logger.info("Starting Tidal Music initial setup...")
        try:
            for uid in self.tidal_user_ids:
                logger.info(f"Tidal Music initial setup for user {uid}...")
                if not self.tidal_controller.force_stop(uid):
                    logger.warning(f"Failed to close Tidal Music for user {uid}")
                time.sleep(2)
                if not self.tidal_controller.handle_isoclipboard(uid):
                    logger.error(
                        f"Tidal Music iso-clipboard setup failed for user {uid}"
                    )
                    return False

            # Wait for playback to start before minimizing
            logger.info("Waiting for playback to start...")
            time.sleep(8)
            if not self.tidal_controller.manage_window_state(True):
                logger.warning("Failed to minimize Tidal Music window")

            logger.info("Tidal Music initial setup completed for all users")
            return True
        except Exception as e:
            logger.error(f"Error in Tidal init setup: {e}")
            return False

    @with_device_lock
    def _beatport_initial_setup(self) -> bool:
        """Initial setup for Beatport for all users, respecting per-user limits."""
        logger.info("Starting Beatport initial setup...")
        try:
            for uid in self.beatport_user_ids:
                if self.beatport_controller.check_daily_limit_reached(user_id=uid):
                    logger.warning(
                        f"Beatport daily limit already reached for user {uid}, skipping setup"
                    )
                    continue

                logger.info(f"Beatport initial setup for user {uid}...")
                if not self.beatport_controller.force_stop(uid):
                    logger.warning(f"Failed to close Beatport for user {uid}")
                time.sleep(2)
                if not self.beatport_controller.handle_initial_setup(uid):
                    logger.error(f"Beatport initial setup failed for user {uid}")
                    return False

            # Wait for playback to start before minimizing
            logger.info("Waiting for playback to start...")
            time.sleep(8)
            
            if not self.beatport_controller.manage_window_state(
                self.beatport_user_ids[0], True
            ):
                logger.warning("Failed to minimize Beatport window")

            logger.info("Beatport initial setup completed for all users")
            return True
        except Exception as e:
            logger.error(f"Error in Beatport init setup: {e}")
            return False

    # -------------------------------------------------------------------------
    # Start / stop / pause / resume
    # -------------------------------------------------------------------------
    def start_automation(self) -> bool:
        """Start automation for all available controllers."""
        if self.running:
            logger.warning("Automation already running")
            return False

        controllers_available = any(
            [
                self.youtube_controller,
                self.apple_controller,
                self.amazon_controller,
                self.tidal_controller,
                self.beatport_controller,
            ]
        )
        if not controllers_available:
            logger.error("No music controllers available")
            return False

        # Initial setups
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

        self.running = True
        now = time.time()

        # Start action worker
        self.action_thread = threading.Thread(
            target=self._process_actions, daemon=True
        )
        self.action_thread.start()
        logger.info("Started action processing thread")

        if self.youtube_controller:
            self.next_iso_youtube = now + self.get_isoclipboard_delay("youtube")
            self.last_youtube_action = now
            self.youtube_thread = threading.Thread(
                target=self._youtube_loop, daemon=True
            )
            self.youtube_thread.start()
            logger.info("Launched YouTube Music automation thread")

        if self.apple_controller:
            self.next_iso_apple = now + self.get_isoclipboard_delay("apple")
            self.last_apple_action = now
            for uid in self.apple_user_ids:
                t = threading.Thread(
                    target=self._apple_loop_for_user, args=(uid,), daemon=True
                )
                t.start()
                self.apple_threads[uid] = t
                logger.info(f"Launched Apple Music automation thread for user {uid}")

        if self.amazon_controller:
            self.next_iso_amazon = now + self.get_isoclipboard_delay("amazon")
            self.last_amazon_action = now
            self.amazon_thread = threading.Thread(
                target=self._amazon_loop, daemon=True
            )
            self.amazon_thread.start()
            logger.info("Launched Amazon Music automation thread")

        if self.tidal_controller:
            self.next_iso_tidal = now + self.get_isoclipboard_delay("tidal")
            self.last_tidal_action = now
            for uid in self.tidal_user_ids:
                t = threading.Thread(
                    target=self._tidal_loop_for_user, args=(uid,), daemon=True
                )
                t.start()
                self.tidal_threads[uid] = t
                logger.info(f"Launched Tidal Music automation thread for user {uid}")

        if self.beatport_controller:
            self.next_beatport_check = now + random.randint(60, 180)
            self.last_beatport_action = now
            for uid in self.beatport_user_ids:
                t = threading.Thread(
                    target=self._beatport_loop_for_user, args=(uid,), daemon=True
                )
                t.start()
                self.beatport_threads[uid] = t
                logger.info(f"Launched Beatport automation thread for user {uid}")

        logger.info("All requested automation threads started")
        return True

    def stop_automation(self):
        """Stop automation for all running controllers."""
        if not self.running:
            logger.warning("No automation is currently running to stop.")
            return

        logger.info("Stopping automation...")
        self.running = False

        # Join app threads
        if self.youtube_thread and self.youtube_thread.is_alive():
            self.youtube_thread.join(timeout=5)
            self.youtube_thread = None

        if self.amazon_thread and self.amazon_thread.is_alive():
            self.amazon_thread.join(timeout=5)
            self.amazon_thread = None

        for uid, t in list(self.apple_threads.items()):
            if t and t.is_alive():
                t.join(timeout=5)
            self.apple_threads[uid] = None

        for uid, t in list(self.tidal_threads.items()):
            if t and t.is_alive():
                t.join(timeout=5)
            self.tidal_threads[uid] = None

        for uid, t in list(self.beatport_threads.items()):
            if t and t.is_alive():
                t.join(timeout=5)
            self.beatport_threads[uid] = None

        # Join action worker
        if self.action_thread and self.action_thread.is_alive():
            # Let queue drain
            try:
                self.action_queue.join()
            except Exception:
                pass
            self.action_thread.join(timeout=5)
            self.action_thread = None

        # Reset timestamps
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

        logger.info("Automation stopped successfully.")

    def pause_automation(self) -> bool:
        if not self.running:
            logger.warning("No automation is currently running")
            return False
        if self.paused:
            logger.warning("Automation is already paused")
            return False
        logger.info("Pausing automation...")
        self.paused = True
        return True

    def resume_automation(self) -> bool:
        if not self.running:
            logger.warning("No automation is currently running")
            return False
        if not self.paused:
            logger.warning("Automation is not paused")
            return False
        logger.info("Resuming automation...")
        self.paused = False
        return True

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------
    def get_status(self) -> dict:
        """Get a simple status snapshot."""
        status = {
            "running": self.running,
            "paused": self.paused,
            "active_apps": [],
        }
        if self.youtube_controller:
            status["active_apps"].append("YouTube Music")
            if self.last_youtube_action > 0:
                status["last_youtube_action"] = time.strftime(
                    "%H:%M:%S", time.localtime(self.last_youtube_action)
                )
            if self.next_iso_youtube > 0:
                status["next_youtube_iso"] = time.strftime(
                    "%H:%M:%S", time.localtime(self.next_iso_youtube)
                )

        if self.apple_controller:
            status["active_apps"].append("Apple Music")
            if self.last_apple_action > 0:
                status["last_apple_action"] = time.strftime(
                    "%H:%M:%S", time.localtime(self.last_apple_action)
                )
            if self.next_iso_apple > 0:
                status["next_apple_iso"] = time.strftime(
                    "%H:%M:%S", time.localtime(self.next_iso_apple)
                )

        if self.amazon_controller:
            status["active_apps"].append("Amazon Music")
            if self.last_amazon_action > 0:
                status["last_amazon_action"] = time.strftime(
                    "%H:%M:%S", time.localtime(self.last_amazon_action)
                )
            if self.next_iso_amazon > 0:
                status["next_amazon_iso"] = time.strftime(
                    "%H:%M:%S", time.localtime(self.next_iso_amazon)
                )

        if self.tidal_controller:
            status["active_apps"].append("Tidal Music")
            if self.last_tidal_action > 0:
                status["last_tidal_action"] = time.strftime(
                    "%H:%M:%S", time.localtime(self.last_tidal_action)
                )
            if self.next_iso_tidal > 0:
                status["next_tidal_iso"] = time.strftime(
                    "%H:%M:%S", time.localtime(self.next_iso_tidal)
                )

        if self.beatport_controller:
            status["active_apps"].append("Beatport")
            if self.last_beatport_action > 0:
                status["last_beatport_action"] = time.strftime(
                    "%H:%M:%S", time.localtime(self.last_beatport_action)
                )
            if self.next_beatport_check > 0:
                status["next_beatport_check"] = time.strftime(
                    "%H:%M:%S", time.localtime(self.next_beatport_check)
                )
            # uses aggregate fields from BeatportMusicController
            hours_played = self.beatport_controller.daily_playtime_seconds / 3600.0
            hours_remaining = (
                self.beatport_controller.daily_limit_hours - hours_played
            )
            status["beatport_hours_played"] = round(hours_played, 2)
            status["beatport_hours_remaining"] = round(max(0, hours_remaining), 2)
            status["beatport_daily_limit"] = self.beatport_controller.daily_limit_hours
            status["beatport_limit_reached"] = hours_remaining <= 0

        return status

    # -------------------------------------------------------------------------
    # Single-app start helpers (used by CLI)
    # -------------------------------------------------------------------------
    def start_apple_only(self) -> bool:
        if not self.apple_controller:
            logger.error("No Apple Music controller available")
            return False
        if not self._apple_initial_setup():
            logger.error("Apple Music initial setup failed")
            return False

        self.running = True
        now = time.time()

        self.action_thread = threading.Thread(
            target=self._process_actions, daemon=True
        )
        self.action_thread.start()

        self.next_iso_apple = now + self.get_isoclipboard_delay("apple")
        self.last_apple_action = now
        for uid in self.apple_user_ids:
            t = threading.Thread(
                target=self._apple_loop_for_user, args=(uid,), daemon=True
            )
            t.start()
            self.apple_threads[uid] = t
            logger.info(f"Started Apple Music automation for user {uid}")
        return True

    def start_tidal_only(self) -> bool:
        if not self.tidal_controller:
            logger.error("No Tidal Music controller available")
            return False
        if not self._tidal_initial_setup():
            logger.error("Tidal Music initial setup failed")
            return False

        self.running = True
        now = time.time()

        self.action_thread = threading.Thread(
            target=self._process_actions, daemon=True
        )
        self.action_thread.start()

        self.next_iso_tidal = now + self.get_isoclipboard_delay("tidal")
        self.last_tidal_action = now
        for uid in self.tidal_user_ids:
            t = threading.Thread(
                target=self._tidal_loop_for_user, args=(uid,), daemon=True
            )
            t.start()
            self.tidal_threads[uid] = t
            logger.info(f"Started Tidal Music automation for user {uid}")
        return True

    def start_beatport_only(self) -> bool:
        if not self.beatport_controller:
            logger.error("No Beatport controller available")
            return False
        if not self._beatport_initial_setup():
            logger.error("Beatport initial setup failed")
            return False

        self.running = True
        now = time.time()

        self.action_thread = threading.Thread(
            target=self._process_actions, daemon=True
        )
        self.action_thread.start()

        self.next_beatport_check = now + random.randint(60, 180)
        self.last_beatport_action = now
        for uid in self.beatport_user_ids:
            t = threading.Thread(
                target=self._beatport_loop_for_user, args=(uid,), daemon=True
            )
            t.start()
            self.beatport_threads[uid] = t
            logger.info(f"Started Beatport automation for user {uid}")
        return True

    def start_youtube_only(self) -> bool:
        if not self.youtube_controller:
            logger.error("No YouTube Music controller available")
            return False
        if not self._youtube_initial_setup():
            logger.error("YouTube Music initial setup failed")
            return False

        self.running = True
        now = time.time()

        self.action_thread = threading.Thread(
            target=self._process_actions, daemon=True
        )
        self.action_thread.start()

        self.next_iso_youtube = now + self.get_isoclipboard_delay("youtube")
        self.last_youtube_action = now
        self.youtube_thread = threading.Thread(
            target=self._youtube_loop, daemon=True
        )
        self.youtube_thread.start()
        logger.info("Started YouTube Music automation")
        return True

    def start_amazon_only(self) -> bool:
        if not self.amazon_controller:
            logger.error("No Amazon Music controller available")
            return False
        if not self._amazon_initial_setup():
            logger.error("Amazon Music initial setup failed")
            return False

        self.running = True
        now = time.time()

        self.action_thread = threading.Thread(
            target=self._process_actions, daemon=True
        )
        self.action_thread.start()

        self.next_iso_amazon = now + self.get_isoclipboard_delay("amazon")
        self.last_amazon_action = now
        self.amazon_thread = threading.Thread(
            target=self._amazon_loop, daemon=True
        )
        self.amazon_thread.start()
        logger.info("Started Amazon Music automation")
        return True
