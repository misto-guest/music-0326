# src/controllers/app_controllers/beatport_music.py

import json
import os
import time
import threading
from datetime import datetime, date
from typing import Dict, Optional

import uiautomator2 as u2

from src.controllers.base_controller import BaseController
from src.controllers.mixins.popup_monitor import PopupMonitorMixin
from src.utils.logging_utils import setup_logger


class BeatportMusicConfig:
    """Configuration for Beatport Music app."""
    APP_NAME = "Beatport Music"
    PACKAGE_NAME = "com.beatport.mobile"
    MAIN_ACTIVITY = ".features.splash.SplashActivity"
    STARTUP_DELAY = 10  # Delay after starting app


logger = setup_logger(__name__)


def save_playtime(device_id: str, user_id: int, playtime_seconds: float, date_str: str) -> None:
    """Save per-user playtime data to a simple file."""
    data = {
        "device_id": device_id,
        "user_id": user_id,
        "playtime_seconds": playtime_seconds,
        "date": date_str,
    }

    # Separate file per device + user
    filename = f"beatport_{device_id}_u{user_id}_playtime.json"

    try:
        with open(filename, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Error saving Beatport playtime for user {user_id}: {e}")


def load_playtime(device_id: str, user_id: int):
    """Load per-user playtime data from file."""
    filename = f"beatport_{device_id}_u{user_id}_playtime.json"

    if not os.path.exists(filename):
        return None, None

    try:
        with open(filename, "r") as f:
            data = json.load(f)
            return data.get("playtime_seconds", 0), data.get("date", None)
    except Exception as e:
        logger.error(f"Error loading Beatport playtime for user {user_id}: {e}")
        return None, None


class BeatportMusicController(BaseController, PopupMonitorMixin):
    """Controller for Beatport music automation with per-user daily playtime limit."""

    def __init__(self, device: u2.Device):
        """Initialize Beatport controller."""
        # Initialize parent classes
        BaseController.__init__(self, device)
        PopupMonitorMixin.__init__(self)

        # App configuration
        self.package_name = BeatportMusicConfig.PACKAGE_NAME
        self.app_name = BeatportMusicConfig.APP_NAME

        # Get device ID for persistence
        try:
            self.device_id = device.serial
        except Exception:
            self.device_id = "unknown"

        # Global daily limit (applies per user)
        self.daily_limit_hours: float = 4.0

        # --- Per-user state ---
        # These dicts are keyed by user_id (e.g. 0, 11, etc.)
        self.user_daily_playtime_seconds: Dict[int, float] = {}
        self.user_last_start_time: Dict[int, Optional[datetime]] = {}
        self.user_is_playing: Dict[int, bool] = {}
        self.user_is_stopping: Dict[int, bool] = {}
        self.user_last_tracking_date: Dict[int, date] = {}

        # --- Legacy aggregate fields (for compatibility with existing code) ---
        # These represent the *sum* across all users and are updated whenever
        # per-user tracking is updated.
        self.daily_playtime_seconds: float = 0.0
        self.last_start_time: Optional[datetime] = None
        self.is_playing: bool = False
        self.is_stopping: bool = False
        self.last_tracking_date: date = date.today()

        # Lock for all state
        self.state_lock = threading.Lock()

        # We lazily load per-user state when a given user_id is first used.

        # Register for popup monitoring
        self.register_app_for_monitoring("Beatport Music")

        # Screen settings
        if not self.setup_screen_settings():
            logger.warning("Failed to set up screen settings during initialization")

        # Save rotation state
        self.initial_rotation_state = self.get_rotation_settings()

    def __del__(self):
        """Cleanup when controller is deleted."""
        try:
            # Flush playtime for all users if there was an active session
            with self.state_lock:
                for user_id, is_playing in list(self.user_is_playing.items()):
                    if is_playing and self.user_last_start_time.get(user_id):
                        self._update_playtime(user_id)
            logger.info("Cleaning up Beatport Music controller")
        except Exception as e:
            logger.error(f"Error in Beatport cleanup: {e}")

    # -------------------------------------------------------------------------
    # Generic helpers
    # -------------------------------------------------------------------------

    def _ensure_user_state(self, user_id: int) -> None:
        """Ensure per-user tracking structures are initialized and loaded."""
        if user_id in self.user_last_tracking_date:
            return

        # Initialize defaults
        self.user_daily_playtime_seconds[user_id] = 0.0
        self.user_last_start_time[user_id] = None
        self.user_is_playing[user_id] = False
        self.user_is_stopping[user_id] = False
        self.user_last_tracking_date[user_id] = date.today()

        # Load saved playtime if it exists and is from today
        saved_playtime, saved_date = load_playtime(self.device_id, user_id)
        if saved_playtime is not None and saved_date == date.today().isoformat():
            self.user_daily_playtime_seconds[user_id] = float(saved_playtime)
            self.user_last_tracking_date[user_id] = date.today()
            logger.info(
                f"Loaded Beatport playtime for user {user_id}: "
                f"{saved_playtime / 3600:.2f} hours"
            )

        # Update aggregate representation
        self._update_aggregate_state_locked()

    def _update_aggregate_state_locked(self) -> None:
        """Update legacy aggregate fields from per-user state (caller holds lock)."""
        total_seconds = sum(self.user_daily_playtime_seconds.values())
        self.daily_playtime_seconds = total_seconds

        # Pick the most recent tracking date among users, or today
        if self.user_last_tracking_date:
            self.last_tracking_date = max(self.user_last_tracking_date.values())
        else:
            self.last_tracking_date = date.today()

        # If *any* user is playing, aggregate is_playing is True
        self.is_playing = any(self.user_is_playing.values())
        self.is_stopping = any(self.user_is_stopping.values())

        # Last start time is arbitrarily the latest among users
        if self.user_last_start_time:
            self.last_start_time = max(
                (dt for dt in self.user_last_start_time.values() if dt is not None),
                default=None,
            )

    # -------------------------------------------------------------------------
    # Screen / rotation helpers
    # -------------------------------------------------------------------------

    def get_rotation_settings(self) -> Dict[str, str]:
        """Get current rotation settings."""
        try:
            auto_rotate = self.device.shell(
                "settings get system accelerometer_rotation"
            ).output.strip()
            user_rotation = self.device.shell(
                "settings get system user_rotation"
            ).output.strip()
            return {"auto_rotate": auto_rotate, "user_rotation": user_rotation}
        except Exception as e:
            logger.error(f"Error getting rotation settings: {e}")
            return {}

    def setup_screen_settings(self) -> bool:
        """Ensure screen stays on."""
        try:
            logger.info("Setting up screen settings")
            self.device.shell(
                "settings put system screen_off_timeout 1800000"
            )  # 30 min
            self.device.shell(
                "settings put global stay_on_while_plugged_in 3"
            )  # Stay awake on AC/USB
            timeout = self.device.shell("settings get system screen_off_timeout")
            if "1800000" in str(timeout):
                logger.info("Screen settings configured successfully")
                return True
            else:
                logger.error("Failed to verify screen settings")
                return False
        except Exception as e:
            logger.error(f"Error setting up screen settings: {e}")
            return False

    def _force_disable_rotation(self) -> bool:
        """Force disable rotation with verification."""
        try:
            for _ in range(3):
                self.device.shell("settings put system accelerometer_rotation 0")
                time.sleep(0.5)
                current = self.device.shell(
                    "settings get system accelerometer_rotation"
                ).output.strip()
                if current == "0":
                    logger.info("Successfully disabled rotation")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error forcing rotation disable: {e}")
            return False

    def _verify_rotation_disabled(self) -> bool:
        """Verify rotation is disabled and fix if needed."""
        try:
            current = self.device.shell(
                "settings get system accelerometer_rotation"
            ).output.strip()
            if current != "0":
                logger.warning("Rotation got enabled, forcing disable")
                return self._force_disable_rotation()
            return True
        except Exception as e:
            logger.error(f"Error verifying rotation: {e}")
            return False

    def _restore_rotation_state(self, initial_state: dict) -> None:
        """Restore rotation to initial state."""
        try:
            if "auto_rotate" in initial_state:
                self.device.shell(
                    f'settings put system accelerometer_rotation {initial_state["auto_rotate"]}'
                )
            if "user_rotation" in initial_state:
                self.device.shell(
                    f'settings put system user_rotation {initial_state["user_rotation"]}'
                )
            logger.info("Restored initial rotation state")
        except Exception as e:
            logger.error(f"Error restoring rotation state: {e}")

    def ensure_screen_active(self) -> bool:
        """Ensure screen is active."""
        try:
            screen_state = self.device.info.get("screenOn")
            if not screen_state:
                self.device.press("power")
                time.sleep(2)
                if not self.device.info.get("screenOn"):
                    logger.error("Failed to activate screen")
                    return False
            logger.info("Screen is active")
            return True
        except Exception as e:
            logger.error(f"Error ensuring screen active: {e}")
            return False

    # -------------------------------------------------------------------------
    # Per-user time tracking
    # -------------------------------------------------------------------------

    def _reset_daily_playtime(self, user_id: int) -> None:
        """Reset per-user playtime if new day has started."""
        with self.state_lock:
            self._ensure_user_state(user_id)

            current_date = date.today()
            last_date = self.user_last_tracking_date[user_id]

            if current_date != last_date:
                previous_hours = self.user_daily_playtime_seconds[user_id] / 3600.0
                logger.info(
                    f"New day detected for user {user_id} ({current_date}), "
                    f"resetting playtime from {previous_hours:.2f}h to 0"
                )

                # Reset counters
                self.user_last_tracking_date[user_id] = current_date
                self.user_daily_playtime_seconds[user_id] = 0.0

                # Save the reset state
                save_playtime(
                    self.device_id,
                    user_id,
                    self.user_daily_playtime_seconds[user_id],
                    current_date.isoformat(),
                )

                # If currently playing, restart tracking from now
                if self.user_is_playing[user_id]:
                    self.user_last_start_time[user_id] = datetime.now()
                    logger.info(
                        f"Resetting ongoing session start time to now for user {user_id}"
                    )

                # Update legacy aggregate
                self._update_aggregate_state_locked()

    def _update_playtime(self, user_id: int) -> None:
        """Update accumulated playtime for a specific user and check limit."""
        with self.state_lock:
            self._ensure_user_state(user_id)

            if (
                not self.user_is_playing[user_id]
                or self.user_is_stopping[user_id]
                or not self.user_last_start_time[user_id]
            ):
                logger.debug(
                    f"Update playtime called for user {user_id} but not playing or stopping"
                )
                return

            # First check for day change
            self._reset_daily_playtime(user_id)

            current_time = datetime.now()
            elapsed = (current_time - self.user_last_start_time[user_id]).total_seconds()

            # Sanity check: avoid adding unreasonable amounts
            if elapsed > 300:
                logger.warning(
                    f"Suspicious elapsed time for user {user_id}: "
                    f"{elapsed / 60:.2f} minutes. Capping at 2 minutes."
                )
                elapsed = 120

            previous_hours = self.user_daily_playtime_seconds[user_id] / 3600.0
            self.user_daily_playtime_seconds[user_id] += elapsed
            hours_played = self.user_daily_playtime_seconds[user_id] / 3600.0

            # Save per-user playtime
            save_playtime(
                self.device_id,
                user_id,
                self.user_daily_playtime_seconds[user_id],
                self.user_last_tracking_date[user_id].isoformat(),
            )

            logger.info(
                f"Updated playtime for user {user_id}: {hours_played:.2f}h "
                f"(+{elapsed / 60:.2f}min)"
            )

            # Update start time
            self.user_last_start_time[user_id] = current_time

            # Sync aggregate
            self._update_aggregate_state_locked()

            # Check if this user just crossed the limit
            if (
                hours_played >= self.daily_limit_hours
                and previous_hours < self.daily_limit_hours
            ):
                logger.warning(
                    f"Daily limit reached for user {user_id} during playback update"
                )
                self.user_is_playing[user_id] = False
                self.user_is_stopping[user_id] = True
                threading.Thread(
                    target=self._safe_force_stop, args=(user_id,)
                ).start()

    def _start_playtime_tracking(self, user_id: int = 0) -> None:
        """Begin counting time for a user."""
        self._reset_daily_playtime(user_id)
        with self.state_lock:
            self._ensure_user_state(user_id)
            if not self.user_is_playing[user_id]:
                self.user_last_start_time[user_id] = datetime.now()
                self.user_is_playing[user_id] = True
                logger.info(
                    f"Started playtime tracking for user {user_id} at "
                    f"{self.user_last_start_time[user_id].strftime('%H:%M:%S')}"
                )
                self._update_aggregate_state_locked()

    def _stop_playtime_tracking(self, user_id: int = 0) -> None:
        """Stop counting time for a user."""
        with self.state_lock:
            self._ensure_user_state(user_id)
            if self.user_is_playing[user_id]:
                # This will update + flip to not playing
                self._update_playtime(user_id)
                self.user_is_playing[user_id] = False
                logger.info(
                    f"Stopped playtime tracking for user {user_id}. "
                    f"Total today: {self.user_daily_playtime_seconds[user_id] / 3600:.2f} hours"
                )
                self._update_aggregate_state_locked()

    def check_daily_limit_reached(self, user_id: int = 0, force_check: bool = False) -> bool:
        """Check if daily limit is reached for a specific user."""
        # First check for day change
        self._reset_daily_playtime(user_id)

        with self.state_lock:
            self._ensure_user_state(user_id)

            # Update current session time if playing
            if self.user_is_playing[user_id] and force_check:
                self._update_playtime(user_id)

            hours_played = self.user_daily_playtime_seconds[user_id] / 3600.0

            if hours_played >= self.daily_limit_hours:
                logger.warning(
                    f"Daily limit reached for user {user_id}: "
                    f"{hours_played:.2f} / {self.daily_limit_hours}h "
                    f"(Date: {self.user_last_tracking_date[user_id]})"
                )

                if self.user_is_playing[user_id]:
                    logger.warning(
                        f"Daily limit reached while playing for user {user_id} - stopping playback"
                    )
                    return self.force_stop_on_limit(user_id=user_id, prevent_recursion=True)

                return True
            else:
                logger.info(
                    f"Playtime status for user {user_id}: "
                    f"{hours_played:.2f} hours of {self.daily_limit_hours} "
                    f"hour daily limit (Date: {self.user_last_tracking_date[user_id]})"
                )
                return False

    # -------------------------------------------------------------------------
    # Force-stop helpers
    # -------------------------------------------------------------------------

    def force_stop_on_limit(self, user_id: int = 0, prevent_recursion: bool = False) -> bool:
        """Force stop Beatport when daily limit is reached for a user."""
        with self.state_lock:
            self._ensure_user_state(user_id)

            if self.user_is_stopping[user_id]:
                logger.warning(
                    f"Already in process of stopping for user {user_id} - ignoring duplicate request"
                )
                return True

            self.user_is_stopping[user_id] = True

        try:
            logger.warning(f"Force stopping Beatport for user {user_id} due to daily limit")

            # Force stop only this user's instance
            self.device.shell(f"am force-stop --user {user_id} {self.package_name}")
            time.sleep(1)

            with self.state_lock:
                self.user_is_playing[user_id] = False
                self.user_is_stopping[user_id] = False
                self._update_aggregate_state_locked()

            logger.info(f"Successfully force-stopped Beatport for user {user_id} on daily limit")
            return True
        except Exception as e:
            with self.state_lock:
                self.user_is_stopping[user_id] = False
                self._update_aggregate_state_locked()
            logger.error(f"Error force stopping Beatport on limit for user {user_id}: {e}")
            return False

    def handle_isoclipboard(self, user_id: int) -> bool:
        """Not used in Beatport; delegates to initial setup for this user."""
        logger.info(
            "Beatport doesn't use IsoClipboard - using initial setup instead "
            f"for user {user_id}"
        )
        return self.handle_initial_setup(user_id)

    # -------------------------------------------------------------------------
    # Initial setup / UI flows
    # -------------------------------------------------------------------------

    def handle_initial_setup(self, user_id: int) -> bool:
        """Full UI setup for Beatport with per-user playtime init."""
        try:
            if self.check_daily_limit_reached(user_id=user_id):
                logger.warning(f"Can't start Beatport for user {user_id} - daily limit reached")
                return False

            logger.info(
                f"Performing initial Beatport setup with forced restart for user {user_id}..."
            )

            # Save any existing playtime for this user first
            with self.state_lock:
                if self.user_is_playing.get(user_id, False):
                    self._update_playtime(user_id)
                    self.user_is_playing[user_id] = False

            if not self._force_disable_rotation():
                logger.error("Failed to disable rotation")
                return False

            if not self.restart_app(user_id):
                logger.error("Failed to restart Beatport")
                return False

            time.sleep(BeatportMusicConfig.STARTUP_DELAY)

            if not self._perform_initial_setup():
                logger.error("Beatport UI setup failed")
                return False

            if not self._handle_shuffle_and_play(user_id):
                logger.error("Failed to start Beatport playback")
                return False

            # Start fresh tracking for this user
            self._start_playtime_tracking(user_id)

            if not self.manage_window_state(user_id, minimize=True):
                logger.warning("Failed to minimize Beatport window")
            else:
                logger.info("Beatport window minimized successfully.")

            logger.info(f"Beatport initial setup completed successfully for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error during Beatport setup for user {user_id}: {e}")
            return False

    def _perform_initial_setup(self) -> bool:
        """Initial UI sequence: main graph, library, playlist, shuffle."""
        try:
            logger.info("Performing Beatport initial UI sequence...")

            main_graph = self.device(resourceId="com.beatport.mobile:id/main_graph")
            if main_graph.exists:
                main_graph.click()
                logger.info("Clicked main graph")
            else:
                logger.error("Main graph element not found")
                return False
            time.sleep(2)

            library_graph = self.device(resourceId="com.beatport.mobile:id/library_graph")
            if library_graph.exists:
                library_graph.click()
                logger.info("Clicked library graph")
            else:
                logger.error("Library graph element not found")
                return False
            time.sleep(3)

            playlist_item = self.device(
                resourceId="com.beatport.mobile:id/constraintLayoutPlaylistItem"
            )
            if playlist_item.exists:
                playlist_item.click()
                logger.info("Clicked playlist item")
            else:
                logger.error("Playlist item element not found")
                return False
            time.sleep(3)

            shuffle_button = self.device(
                resourceId="com.beatport.mobile:id/linearLayoutShuffle"
            )
            if shuffle_button.exists:
                shuffle_button.click()
                logger.info("Clicked shuffle button")
            else:
                logger.error("Shuffle button element not found")
                return False
            time.sleep(1)

            return True
        except Exception as e:
            logger.error(f"Error in Beatport UI sequence: {e}")
            return False

    def _handle_shuffle_and_play(self, user_id: int) -> bool:
        """Ensure playback actually starts after shuffle click."""
        logger.info(f"Confirming playback is active after shuffle for user {user_id}...")

        time.sleep(3)

        play_button = self.device(resourceId=f"{self.package_name}:id/playPauseButton")
        if play_button.exists:
            button_desc = play_button.info.get("contentDescription", "").lower()
            if "play" in button_desc and "pause" not in button_desc:
                logger.warning("Playback appears to be paused, attempting to start...")
                play_button.click()
                time.sleep(2)

        time.sleep(2)

        with self.state_lock:
            self._ensure_user_state(user_id)
            logger.info(f"Marking playback as active for user {user_id}")
            self.user_is_playing[user_id] = True
            self.user_last_start_time[user_id] = datetime.now()
            self._update_aggregate_state_locked()

        return True

    # -------------------------------------------------------------------------
    # App / window management
    # -------------------------------------------------------------------------

    def prepare_for_action(self, user_id: int) -> bool:
        """Ensure we can safely interact with app for a given user."""
        try:
            if self.check_daily_limit_reached(user_id=user_id):
                logger.warning(
                    f"Daily limit reached for user {user_id} - cannot prepare for action"
                )
                return False

            if not self.ensure_screen_active():
                logger.error("Failed to ensure screen is active")
                return False

            # Update time before any potential restarts
            self._update_playtime(user_id)

            if self._verify_app_running(user_id):
                return True

            # App needs restart - remember per-user state
            with self.state_lock:
                was_playing = self.user_is_playing.get(user_id, False)

            if not self.start_app(user_id):
                return False

            time.sleep(1)
            running = self._verify_app_running(user_id)

            with self.state_lock:
                if running and was_playing:
                    self.user_is_playing[user_id] = True
                    self.user_last_start_time[user_id] = datetime.now()
                    self._update_aggregate_state_locked()

            return running

        except Exception as e:
            logger.error(f"Error preparing for action for user {user_id}: {e}")
            return False

    def play_pause(self, user_id: int, check_limit: bool = True) -> bool:
        """Toggle play/pause with per-user daily limit checks."""
        if self.user_is_playing.get(user_id, False):
            self._stop_playtime_tracking(user_id)
        else:
            if check_limit and self.check_daily_limit_reached(user_id=user_id):
                logger.warning(
                    f"Cannot start playback for user {user_id} - daily limit reached"
                )
                return False

        start_time = time.time()
        try:
            logger.info(f"Attempting Beatport play/pause for user {user_id}...")
            prepared = False
            while time.time() - start_time < 15:
                if self.prepare_for_action(user_id):
                    prepared = True
                    break
                time.sleep(2)
            if not prepared:
                logger.warning(
                    f"Timed out preparing Beatport for user {user_id}; using keyevent fallback."
                )
                self.device.shell("input keyevent KEYCODE_MEDIA_PLAY_PAUSE")

                if self.user_is_playing.get(user_id, False):
                    self._stop_playtime_tracking(user_id)
                else:
                    self._start_playtime_tracking(user_id)
                return True

            play_button = self.device(resourceId=f"{self.package_name}:id/playPauseButton")
            if play_button.exists:
                play_button.click()
                logger.info("Clicked Beatport play/pause button")
                if self.user_is_playing.get(user_id, False):
                    self._stop_playtime_tracking(user_id)
                else:
                    self._start_playtime_tracking(user_id)
                time.sleep(1)
                return True

            logger.info(
                "Play button not found, using keyevent fallback for play/pause"
            )
            self.device.shell("input keyevent KEYCODE_MEDIA_PLAY_PAUSE")
            if self.user_is_playing.get(user_id, False):
                self._stop_playtime_tracking(user_id)
            else:
                self._start_playtime_tracking(user_id)
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error toggling play/pause for user {user_id}: {e}")
            try:
                self.device.shell("input keyevent KEYCODE_MEDIA_PLAY_PAUSE")
                if self.user_is_playing.get(user_id, False):
                    self._stop_playtime_tracking(user_id)
                else:
                    self._start_playtime_tracking(user_id)
                logger.info("Keyevent fallback successful")
                time.sleep(1)
                return True
            except Exception:
                return False

    def next_track(self, user_id: int) -> bool:
        """Skip to next track with per-user playtime preservation."""
        if self.check_daily_limit_reached(user_id=user_id, force_check=True):
            logger.warning(
                f"Daily limit reached for user {user_id} - cannot perform next track"
            )
            return False

        with self.state_lock:
            if self.user_is_stopping.get(user_id, False):
                logger.warning(
                    f"Cannot perform next track for user {user_id} while stopping"
                )
                return False

        start_time = time.time()
        try:
            logger.info(f"Attempting next track for user {user_id}...")
            prepared = False
            while time.time() - start_time < 15:
                if self.prepare_for_action(user_id):
                    prepared = True
                    break
                time.sleep(2)

                if self.check_daily_limit_reached(user_id=user_id):
                    logger.warning(
                        f"Daily limit reached for user {user_id} during preparation"
                    )
                    return False

            if not prepared:
                logger.warning(
                    f"Timed out preparing for next track for user {user_id}; "
                    "using keyevent fallback"
                )
                self.device.shell("input keyevent KEYCODE_MEDIA_NEXT")
                time.sleep(1)
                return True

            next_button = self.device(
                resourceId=f"{self.package_name}:id/imageNext"
            )
            if next_button.exists:
                next_button.click()
                logger.info("Clicked next track button")
                time.sleep(1)
                return True

            logger.info(
                "Next button not found, using keyevent fallback for next track"
            )
            self.device.shell("input keyevent KEYCODE_MEDIA_NEXT")
            return True

        except Exception as e:
            logger.error(f"Error skipping track for user {user_id}: {e}")
            try:
                self.device.shell("input keyevent KEYCODE_MEDIA_NEXT")
                time.sleep(1)
                return True
            except Exception:
                return False

    def previous_track(self, user_id: int) -> bool:
        """Go to previous track for a specific user."""
        if self.user_is_playing.get(user_id, False) and self.check_daily_limit_reached(
            user_id=user_id
        ):
            logger.warning(
                f"Daily limit reached for user {user_id} - stopping playback instead "
                "of previous track"
            )
            return self.play_pause(user_id)

        start_time = time.time()
        try:
            logger.info(f"Attempting previous track for user {user_id}...")
            prepared = False
            while time.time() - start_time < 15:
                if self.prepare_for_action(user_id):
                    prepared = True
                    break
                time.sleep(2)
            if not prepared:
                logger.warning(
                    f"Timed out; using keyevent fallback for previous track for user {user_id}"
                )
                self.device.shell("input keyevent KEYCODE_MEDIA_PREVIOUS")
                time.sleep(1)
                return True

            prev_button = self.device(
                resourceId=f"{self.package_name}:id/previousButton"
            )
            if prev_button.exists:
                prev_button.click()
                logger.info("Clicked previous track button")
                time.sleep(1)
                return True

            logger.info(
                "Previous button not found, using keyevent fallback for previous track"
            )
            self.device.shell("input keyevent KEYCODE_MEDIA_PREVIOUS")
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error going to previous track for user {user_id}: {e}")
            try:
                self.device.shell("input keyevent KEYCODE_MEDIA_PREVIOUS")
                time.sleep(1)
                return True
            except Exception as ex:
                logger.error(f"Fallback keyevent failed: {ex}")
                return False

    def like_current_song(self, user_id: int) -> bool:
        """Beatport does not support 'like' natively."""
        logger.info("Beatport: like action not supported; skipping.")
        return True

    def _verify_app_running(self, user_id: int) -> bool:
        """Check if Beatport is in foreground for a given user."""
        try:
            result = self.device.shell(
                "dumpsys activity recents | grep " + self.package_name
            )
            command_output = result.output

            if f"u{user_id}" in command_output:
                logger.info(f"Beatport is current app for user {user_id}")
                return True

            return False
        except Exception as e:
            logger.error(f"Error verifying app state for user {user_id}: {e}")
            return False

    def stop_app(self, user_id: int) -> bool:
        """Stop Beatport app and restore rotation state if desired at session end."""
        try:
            self.device.shell(f"am force-stop --user {user_id} {self.package_name}")
            time.sleep(1)
            if self.is_running(user_id):
                logger.warning("App still running after stop attempt, trying force-stop")
                return self.force_stop(user_id)

            if self.initial_rotation_state:
                self._restore_rotation_state(self.initial_rotation_state)
            logger.info("Restored rotation state after stopping Beatport.")
            return True
        except Exception as e:
            logger.error(f"Error stopping Beatport: {e}")
            return False

        except Exception as e:
            logger.error(f"Error stopping Beatport for user {user_id}: {e}")
            return False

    def start_app(self, user_id: int) -> bool:
        """Launch Beatport for specific user if under daily limit."""
        if self.check_daily_limit_reached(user_id=user_id):
            logger.warning(
                f"Cannot start Beatport for user {user_id} - daily limit reached"
            )
            return False

        try:
            logger.info(f"Starting Beatport for user {user_id}...")
            if not self._force_disable_rotation():
                return False

            self.device.shell(
                f"am start --user {user_id} -W -n "
                f"{self.package_name}/{BeatportMusicConfig.MAIN_ACTIVITY} "
                f"--activity-single-top"
            )
            time.sleep(3)

            if self._verify_app_running(user_id):
                logger.info(f"Beatport started via am start for user {user_id}")
                return True

            logger.info(f"Retrying Beatport start for user {user_id}...")
            time.sleep(1)
            if self._verify_app_running(user_id):
                logger.info(f"Beatport started after retry for user {user_id}")
                return True

            logger.error(f"Failed to start Beatport for user {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error starting Beatport for user {user_id}: {e}")
            return False

    def is_running(self, user_id: int) -> bool:
        """Check if Beatport is running for a specific user."""
        try:
            return self._verify_app_running(user_id)
        except Exception as e:
            logger.error(f"Error checking if Beatport is running for user {user_id}: {e}")
            return False

    def force_stop(self, user_id: int = 0) -> bool:
        """Force-stop Beatport for a specific user."""
        try:
            self.device.shell(f"am force-stop --user {user_id} {self.package_name}")
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error force stopping Beatport for user {user_id}: {e}")
            return False

    def manage_window_state(self, user_id: int, minimize: bool = True) -> bool:
        """Minimize/maximize without affecting playback state."""
        try:
            if minimize:
                logger.info(f"Minimizing Beatport window for user {user_id}")
                self.device.press("home")
                time.sleep(1)
                return True
            else:
                logger.info(f"Maximizing Beatport window for user {user_id}")
                if self.is_running(user_id):
                    command = f"monkey -p {self.package_name} -c android.intent.category.LAUNCHER 1"
                    self.device.shell(command)
                    time.sleep(3)
                    return True
                else:
                    return self.start_app(user_id)
        except Exception as e:
            logger.error(
                f"Failed to manage window state for user {user_id}: {e}"
            )
            return False

    def restart_app(self, user_id: int) -> bool:
        """Force-stop and relaunch Beatport for specific user."""
        try:
            logger.info(f"Restarting Beatport for user {user_id}...")
            self.device.shell(f"am force-stop --user {user_id} {self.package_name}")
            time.sleep(2)
            cmd = (
                f"am start --user {user_id} -W -n "
                f"{BeatportMusicConfig.PACKAGE_NAME}/{BeatportMusicConfig.MAIN_ACTIVITY} "
                f"--activity-single-top"
            )
            self.device.shell(cmd)
            time.sleep(3)
            if self._verify_app_running(user_id):
                logger.info(f"Beatport restarted successfully for user {user_id}.")
                return True
            else:
                logger.error(f"Beatport failed to restart for user {user_id}.")
                return False
        except Exception as e:
            logger.error(f"Error restarting Beatport for user {user_id}: {e}")
            return False

    def _safe_force_stop(self, user_id: Optional[int] = None) -> None:
        """
        Safe isolated force stop that won't trigger playtime updates.

        If user_id is None, fall back to a global stop (for backwards compatibility).
        """
        try:
            if user_id is None:
                logger.info("Safe force stop initiated (no user_id, global stop)")
            else:
                logger.info(f"Safe force stop initiated for user {user_id}")

            if user_id is not None:
                with self.state_lock:
                    self._ensure_user_state(user_id)
                    self.user_is_playing[user_id] = False
                    self.user_is_stopping[user_id] = True
                    self._update_aggregate_state_locked()

                self.device.shell(
                    f"am force-stop --user {user_id} {self.package_name}"
                )
                time.sleep(1)

                # Reset state
                with self.state_lock:
                    self.user_is_stopping[user_id] = False
                    self._update_aggregate_state_locked()
            else:
                # Global fallback
                self.is_playing = False
                self.device.app_stop(self.package_name)
                time.sleep(1)
                self.is_stopping = False

            logger.info("Safe force stop completed")
        except Exception as e:
            logger.error(f"Error in safe force stop: {e}")
            with self.state_lock:
                if user_id is not None and user_id in self.user_is_stopping:
                    self.user_is_stopping[user_id] = False
                self._update_aggregate_state_locked()
