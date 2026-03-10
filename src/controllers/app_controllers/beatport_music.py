# src/controllers/app_controllers/beatport_music.py

import json
import os
import time
import threading
from datetime import datetime, date, timedelta
from typing import Dict
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


def save_playtime(device_id, playtime_seconds, date_str):
    """Save playtime data to a simple file."""
    data = {
        "device_id": device_id,
        "playtime_seconds": playtime_seconds,
        "date": date_str
    }

    # Create a simple filename with device ID
    filename = f"beatport_{device_id}_playtime.json"

    with open(filename, 'w') as f:
        json.dump(data, f)


def load_playtime(device_id):
    """Load playtime data from file."""
    filename = f"beatport_{device_id}_playtime.json"

    if not os.path.exists(filename):
        return None, None

    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            return data.get("playtime_seconds", 0), data.get("date", None)
    except:
        return None, None

class BeatportMusicController(BaseController, PopupMonitorMixin):
    """Controller for Beatport music automation with daily 6-hour playtime limit."""

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
        except:
            self.device_id = "unknown"

        # Time tracking attributes
        self.daily_limit_hours = 5
        self.daily_playtime_seconds = 0
        self.last_start_time = None
        self.is_playing = False
        self.is_stopping = False
        self.last_tracking_date = date.today()
        self.state_lock = threading.Lock()

        # Load saved playtime if available and from today
        saved_playtime, saved_date = load_playtime(self.device_id)
        if saved_playtime is not None and saved_date == date.today().isoformat():
            self.daily_playtime_seconds = saved_playtime
            logger.info(f"Loaded saved playtime: {saved_playtime / 3600:.2f} hours")

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
            # Only need to handle Beatport-specific cleanup
            if self.is_playing and self.last_start_time:
                self._update_playtime()
            logger.info("Cleaning up Beatport Music controller")
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")

    def get_rotation_settings(self) -> Dict[str, str]:
        """Get current rotation settings."""
        try:
            auto_rotate = self.device.shell('settings get system accelerometer_rotation').output.strip()
            user_rotation = self.device.shell('settings get system user_rotation').output.strip()
            return {'auto_rotate': auto_rotate, 'user_rotation': user_rotation}
        except Exception as e:
            logger.error(f"Error getting rotation settings: {e}")
            return {}

    def setup_screen_settings(self) -> bool:
        """Ensure screen stays on."""
        try:
            logger.info("Setting up screen settings")
            self.device.shell('settings put system screen_off_timeout 1800000')  # 30 min
            self.device.shell('settings put global stay_on_while_plugged_in 3')  # Stay awake on AC/USB
            timeout = self.device.shell('settings get system screen_off_timeout')
            if '1800000' in str(timeout):
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
                self.device.shell('settings put system accelerometer_rotation 0')
                time.sleep(0.5)
                current = self.device.shell('settings get system accelerometer_rotation').output.strip()
                if current == '0':
                    logger.info("Successfully disabled rotation")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error forcing rotation disable: {e}")
            return False

    def _verify_rotation_disabled(self) -> bool:
        """Verify rotation is disabled and fix if needed."""
        try:
            current = self.device.shell('settings get system accelerometer_rotation').output.strip()
            if current != '0':
                logger.warning("Rotation got enabled, forcing disable")
                return self._force_disable_rotation()
            return True
        except Exception as e:
            logger.error(f"Error verifying rotation: {e}")
            return False

    def _restore_rotation_state(self, initial_state: dict) -> None:
        """Restore rotation to initial state."""
        try:
            if 'auto_rotate' in initial_state:
                self.device.shell(f'settings put system accelerometer_rotation {initial_state["auto_rotate"]}')
            if 'user_rotation' in initial_state:
                self.device.shell(f'settings put system user_rotation {initial_state["user_rotation"]}')
            logger.info("Restored initial rotation state")
        except Exception as e:
            logger.error(f"Error restoring rotation state: {e}")

    def ensure_screen_active(self) -> bool:
        """Ensure screen is active."""
        try:
            screen_state = self.device.info.get('screenOn')
            if not screen_state:
                self.device.press("power")
                time.sleep(2)
                if not self.device.info.get('screenOn'):
                    logger.error("Failed to activate screen")
                    return False
            logger.info("Screen is active")
            return True
        except Exception as e:
            logger.error(f"Error ensuring screen active: {e}")
            return False

    def _reset_daily_playtime(self) -> None:
        """Reset if new day, using date objects for comparison."""
        current_date = date.today()

        if current_date != self.last_tracking_date:
            previous_hours = self.daily_playtime_seconds / 3600
            logger.info(f"New day detected ({current_date}), resetting playtime from {previous_hours:.2f}h to 0")

            # Update tracking date first
            self.last_tracking_date = current_date

            # Reset counters
            self.daily_playtime_seconds = 0

            # Save the reset state
            save_playtime(
                self.device_id,
                self.daily_playtime_seconds,
                self.last_tracking_date.isoformat()
            )

            # If currently playing, start fresh tracking from now
            if self.is_playing:
                self.last_start_time = datetime.now()
                logger.info("Resetting ongoing session start time to now")

    def _update_playtime(self) -> None:
        """Update accumulated playtime and check limit with better safeguards."""
        if not self.is_playing or self.is_stopping or not self.last_start_time:
            logger.debug("Update playtime called but not playing or already stopping")
            return

        try:
            with self.state_lock:  # Use lock for thread safety
                # First check for day change
                self._reset_daily_playtime()

                # Calculate elapsed time
                current_time = datetime.now()
                elapsed = (current_time - self.last_start_time).total_seconds()

                # Sanity check: don't add unreasonable amounts of playtime
                if elapsed > 300:  # If more than 5 minutes has passed, something is wrong
                    logger.warning(f"Suspicious elapsed time: {elapsed / 60:.2f} minutes. Capping at 2 minutes.")
                    elapsed = 120  # Cap at 2 minutes

                previous_hours = self.daily_playtime_seconds / 3600
                self.daily_playtime_seconds += elapsed
                hours_played = self.daily_playtime_seconds / 3600

                # Save playtime data after updating
                save_playtime(
                    self.device_id,
                    self.daily_playtime_seconds,
                    self.last_tracking_date.isoformat()
                )

                logger.info(f"Updated playtime: {hours_played:.2f}h (+{elapsed / 60:.2f}min)")

                # Only update start time first to avoid recursion
                self.last_start_time = current_time

                # Check if we just crossed the limit
                if hours_played >= self.daily_limit_hours and previous_hours < self.daily_limit_hours:
                    logger.warning("Daily limit reached during playback update")
                    # Immediately mark as not playing and start safe stop on separate thread
                    self.is_playing = False
                    self.is_stopping = True
                    threading.Thread(target=self._safe_force_stop).start()

        except Exception as e:
            logger.error(f"Error updating playtime: {e}")

    def _start_playtime_tracking(self) -> None:
        """Begin counting time with proper state initialization."""
        self._reset_daily_playtime()  # Check for day change first

        if not self.is_playing:
            self.last_start_time = datetime.now()
            self.is_playing = True
            logger.info(f"Started playtime tracking at {self.last_start_time.strftime('%H:%M:%S')}")

    def _stop_playtime_tracking(self) -> None:
        """Stop counting time."""
        if self.is_playing:
            self._update_playtime()
            self.is_playing = False
            logger.info(f"Stopped playtime tracking. Total today: {self.daily_playtime_seconds / 3600:.2f} hours")

    def check_daily_limit_reached(self, force_check=False) -> bool:
        """Check if daily limit is reached and handle appropriately."""
        # First check for day change
        self._reset_daily_playtime()

        # Update current session time if playing, but prevent recursive calls
        if self.is_playing and force_check:
            self._update_playtime()

        hours_played = self.daily_playtime_seconds / 3600

        if hours_played >= self.daily_limit_hours:
            logger.warning(
                f"Daily limit reached: {hours_played:.2f} / {self.daily_limit_hours}h "
                f"(Date: {self.last_tracking_date})"
            )

            # Important: Stop playback if we're currently playing
            # Use force_stop_on_limit with a flag to prevent recursion
            if self.is_playing:
                logger.warning("Daily limit reached while playing - stopping playback")
                return self.force_stop_on_limit(prevent_recursion=True)

            return True
        else:
            logger.info(
                f"Playtime status: {hours_played:.2f} hours of {self.daily_limit_hours} "
                f"hour daily limit (Date: {self.last_tracking_date})"
            )
            return False

    def force_stop_on_limit(self, prevent_recursion=False) -> bool:
        """Force stop Beatport when daily limit is reached."""
        # Prevent multiple simultaneous calls
        if self.is_stopping:
            logger.warning("Already in process of stopping - ignoring duplicate request")
            return True

        try:
            self.is_stopping = True

            # Skip UI interactions and go straight to force stop
            logger.warning("Force stopping app due to daily limit")
            self.device.app_stop(self.package_name)
            time.sleep(1)

            # Mark as not playing immediately
            self.is_playing = False

            if self.is_running():
                self.device.app_stop(self.package_name)
                time.sleep(1)

            # Reset state at the end
            self.is_stopping = False
            logger.info("Successfully force-stopped Beatport on daily limit")
            return True
        except Exception as e:
            self.is_stopping = False
            logger.error(f"Error force stopping on limit: {e}")
            return False

    def handle_isoclipboard(self) -> bool:
        """Not used in Beatport; delegates to handle_initial_setup()."""
        logger.info("Beatport doesn't use IsoClipboard - using initial setup instead")
        return self.handle_initial_setup()

    def handle_initial_setup(self) -> bool:
        """Full UI setup for Beatport with proper playtime init."""
        try:
            if self.check_daily_limit_reached():
                logger.warning("Can't start Beatport - daily limit reached")
                return False

            logger.info("Performing initial Beatport setup with forced restart...")

            # Important: Save any existing playtime first
            if self.is_playing:
                self._update_playtime()
                self.is_playing = False  # Reset state for new setup

            if not self._force_disable_rotation():
                logger.error("Failed to disable rotation")
                return False

            if not self.restart_app():
                logger.error("Failed to restart Beatport")
                return False

            time.sleep(BeatportMusicConfig.STARTUP_DELAY)

            if not self._perform_initial_setup():
                logger.error("Beatport UI setup failed")
                return False

            if not self._handle_shuffle_and_play():
                logger.error("Failed to start Beatport playback")
                return False

            # Start fresh tracking
            self._start_playtime_tracking()

            if not self.manage_window_state(minimize=True):
                logger.warning("Failed to minimize Beatport window")
            else:
                logger.info("Beatport window minimized successfully.")

            logger.info("Beatport initial setup completed successfully")
            return True

        except Exception as e:
            logger.error(f"Error during Beatport setup: {e}")
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

            playlist_item = self.device(resourceId="com.beatport.mobile:id/constraintLayoutPlaylistItem")
            if playlist_item.exists:
                playlist_item.click()
                logger.info("Clicked playlist item")
            else:
                logger.error("Playlist item element not found")
                return False
            time.sleep(3)

            shuffle_button = self.device(resourceId="com.beatport.mobile:id/linearLayoutShuffle")
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

    def _handle_shuffle_and_play(self) -> bool:
        """Ensure playback actually starts after shuffle click."""
        logger.info("Confirming playback is active after shuffle...")

        # Give it a moment for playback to start
        time.sleep(3)

        # Check if there's evidence of active playback
        play_button = self.device(resourceId=f"{self.package_name}:id/playPauseButton")
        if play_button.exists:
            button_desc = play_button.info.get("contentDescription", "").lower()

            # If button shows "play" that means we're paused
            if "play" in button_desc and "pause" not in button_desc:
                logger.warning("Playback appears to be paused, attempting to start...")
                play_button.click()
                time.sleep(2)

        # Another check: look for progress bar movement
        time.sleep(2)  # Wait briefly

        # Assume playback is working and mark as playing
        logger.info("Marking playback as active")
        self.is_playing = True
        self.last_start_time = datetime.now()

        return True

    def prepare_for_action(self) -> bool:
        """Ensure we can safely interact with app while preserving time."""
        try:
            if self.check_daily_limit_reached():
                logger.warning("Daily limit reached - cannot prepare for action")
                return False

            if not self.ensure_screen_active():
                logger.error("Failed to ensure screen is active")
                return False

            # Important: Update time before any potential restarts
            if self.is_playing:
                self._update_playtime()

            if self._verify_app_running():
                return True

            # App needs restart - remember state
            was_playing = self.is_playing

            if not self.start_app():
                return False

            time.sleep(1)
            running = self._verify_app_running()

            # Restore playing state after restart
            if running and was_playing:
                self.is_playing = True
                self.last_start_time = datetime.now()

            return running

        except Exception as e:
            logger.error(f"Error preparing for action: {e}")
            return False

    def play_pause(self, check_limit=True) -> bool:
        """Toggle play/pause with daily limit checks."""
        if self.is_playing:
            self._stop_playtime_tracking()
        else:
            if check_limit and self.check_daily_limit_reached():
                logger.warning("Cannot start playback - daily limit reached")
                return False

        start_time = time.time()
        try:
            logger.info("Attempting Beatport play/pause...")
            prepared = False
            while time.time() - start_time < 15:
                if self.prepare_for_action():
                    prepared = True
                    break
                time.sleep(2)
            if not prepared:
                logger.warning("Timed out preparing Beatport; using keyevent fallback.")
                self.device.shell('input keyevent KEYCODE_MEDIA_PLAY_PAUSE')

                if self.is_playing:
                    self._stop_playtime_tracking()
                else:
                    self._start_playtime_tracking()
                return True

            play_button = self.device(resourceId=f"{self.package_name}:id/playPauseButton")
            if play_button.exists:
                play_button.click()
                logger.info("Clicked Beatport play/pause button")
                if self.is_playing:
                    self._stop_playtime_tracking()
                else:
                    self._start_playtime_tracking()
                time.sleep(1)
                return True

            logger.info("Play button not found, using keyevent fallback")
            self.device.shell('input keyevent KEYCODE_MEDIA_PLAY_PAUSE')
            if self.is_playing:
                self._stop_playtime_tracking()
            else:
                self._start_playtime_tracking()
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error toggling play/pause: {e}")
            try:
                self.device.shell('input keyevent KEYCODE_MEDIA_PLAY_PAUSE')
                if self.is_playing:
                    self._stop_playtime_tracking()
                else:
                    self._start_playtime_tracking()
                logger.info("Keyevent fallback successful")
                time.sleep(1)
                return True
            except Exception:
                return False

    def next_track(self) -> bool:
        """Skip to next track with playtime preservation."""
        # Check limit first before any other operations
        if self.check_daily_limit_reached(force_check=True):  # Force check to get latest
            logger.warning("Daily limit reached - cannot perform next track")
            return False

        if self.is_stopping:
            logger.warning("Cannot perform next track while stopping")
            return False

        start_time = time.time()
        try:
            logger.info("Attempting next track...")
            prepared = False
            while time.time() - start_time < 15:
                if self.prepare_for_action():  # This updates playtime
                    prepared = True
                    break
                time.sleep(2)

                # Check limit during preparation
                if self.check_daily_limit_reached():
                    logger.warning("Daily limit reached during preparation")
                    return False

            if not prepared:
                logger.warning("Timed out preparing for next track; using keyevent fallback")
                self.device.shell('input keyevent KEYCODE_MEDIA_NEXT')
                time.sleep(1)
                return True

            next_button = self.device(resourceId=f"{self.package_name}:id/imageNext")
            if next_button.exists:
                next_button.click()
                logger.info("Clicked next track button")
                time.sleep(1)
                return True

            logger.info("Next button not found, using keyevent fallback")
            self.device.shell('input keyevent KEYCODE_MEDIA_NEXT')
            time.sleep(1)
            return True

        except Exception as e:
            logger.error(f"Error skipping track: {e}")
            try:
                self.device.shell('input keyevent KEYCODE_MEDIA_NEXT')
                time.sleep(1)
                return True
            except Exception:
                return False

    def previous_track(self) -> bool:
        """Go to previous track."""
        if self.is_playing and self.check_daily_limit_reached():
            logger.warning("Daily limit reached - stopping playback instead of previous track")
            return self.play_pause()

        start_time = time.time()
        try:
            logger.info("Attempting previous track...")
            prepared = False
            while time.time() - start_time < 15:
                if self.prepare_for_action():
                    prepared = True
                    break
                time.sleep(2)
            if not prepared:
                logger.warning("Timed out; using keyevent fallback for previous track")
                self.device.shell('input keyevent KEYCODE_MEDIA_PREVIOUS')
                time.sleep(1)
                return True

            prev_button = self.device(resourceId=f"{self.package_name}:id/previousButton")
            if prev_button.exists:
                prev_button.click()
                logger.info("Clicked previous track button")
                time.sleep(1)
                return True

            logger.info("Previous button not found, using keyevent fallback")
            self.device.shell('input keyevent KEYCODE_MEDIA_PREVIOUS')
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error going to previous track: {e}")
            try:
                self.device.shell('input keyevent KEYCODE_MEDIA_PREVIOUS')
                time.sleep(1)
                return True
            except Exception as ex:
                logger.error(f"Fallback keyevent failed: {ex}")
                return False

    def like_current_song(self) -> bool:
        """Beatport does not support 'like' natively."""
        logger.info("Beatport: like action not supported; skipping.")
        return True

    def _verify_app_running(self) -> bool:
        """Check if Beatport is in foreground or has visible UI."""
        try:
            if self.device(packageName=self.package_name).exists:
                logger.info("Found Beatport UI elements")
                return True

            current_app = self.device.app_current()
            if current_app.get('package') == self.package_name:
                logger.info("Beatport is current app")
                return True

            # Another fallback: dumpsys check
            if self.package_name in self.device.shell('dumpsys activity activities | grep -i "mResumedActivity"'):
                logger.info("Beatport found in resumed activities")
                return True

            return False
        except Exception as e:
            logger.error(f"Error verifying app state: {e}")
            return False

    def stop_app(self) -> bool:
        """Stop Beatport and save final playtime."""
        try:
            if self.is_playing:
                self._update_playtime()
                self.is_playing = False

            self.device.app_stop(self.package_name)
            time.sleep(1)

            if self.is_running():
                logger.warning("App still running, forcing stop")
                return self.force_stop()

            if self.initial_rotation_state:
                self._restore_rotation_state(self.initial_rotation_state)

            logger.info("Restored rotation state and stopped Beatport")
            return True

        except Exception as e:
            logger.error(f"Error stopping Beatport: {e}")
            return False

    def start_app(self) -> bool:
        """Launch Beatport if under daily limit."""
        if self.check_daily_limit_reached():
            logger.warning("Cannot start Beatport - daily limit reached")
            return False

        try:
            logger.info("Starting Beatport...")
            if not self._force_disable_rotation():
                return False

            self.device.shell(
                f'am start -W -n {self.package_name}/{BeatportMusicConfig.MAIN_ACTIVITY} --activity-single-top'
            )
            time.sleep(3)

            if self._verify_app_running():
                logger.info("Beatport started via am start")
                return True

            logger.info("Retrying Beatport start...")
            time.sleep(1)
            if self._verify_app_running():
                logger.info("Beatport started after retry")
                return True

            logger.error("Failed to start Beatport")
            return False
        except Exception as e:
            logger.error(f"Error starting Beatport: {e}")
            return False

    def is_running(self) -> bool:
        """Check if Beatport is running."""
        try:
            return self._verify_app_running()
        except Exception as e:
            logger.error(f"Error checking if Beatport is running: {e}")
            return False

    def force_stop(self) -> bool:
        """Force-stop Beatport."""
        try:
            self.device.app_stop(self.package_name)
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error force stopping Beatport: {e}")
            return False

    def manage_window_state(self, minimize: bool = True) -> bool:
        """Minimize/maximize without affecting playback state."""
        try:
            if minimize:
                logger.info("Minimizing Beatport window")
                self.device.press("home")
                time.sleep(1)
                return True
            else:
                logger.info("Maximizing Beatport window")
                if self.is_running():
                    command = f"monkey -p {self.package_name} -c android.intent.category.LAUNCHER 1"
                    self.device.shell(command)
                    time.sleep(3)
                    return True
                else:
                    return self.start_app()
        except Exception as e:
            logger.error(f"Failed to manage window state: {e}")
            return False

    def restart_app(self) -> bool:
        """Force-stop and relaunch Beatport."""
        try:
            self.device.app_stop(self.package_name)
            time.sleep(2)
            cmd = f"am start -W -n {BeatportMusicConfig.PACKAGE_NAME}/{BeatportMusicConfig.MAIN_ACTIVITY} --activity-single-top"
            self.device.shell(cmd)
            time.sleep(3)
            if self._verify_app_running():
                logger.info("Beatport restarted successfully.")
                return True
            else:
                logger.error("Beatport failed to restart.")
                return False
        except Exception as e:
            logger.error(f"Error restarting Beatport: {e}")
            return False

    def _safe_force_stop(self):
        """Safe isolated force stop that won't trigger playtime updates."""
        try:
            logger.info("Safe force stop initiated")

            # Ensure we're no longer tracking time
            self.is_playing = False

            # Force stop the app directly without UI interactions
            self.device.app_stop(self.package_name)
            time.sleep(1)

            # Double-check it's really stopped
            if self.is_running():
                logger.warning("App still running after stop, trying force-stop again")
                self.device.app_stop(self.package_name)
                time.sleep(3)

            # Reset state
            self.is_stopping = False
            logger.info("Safe force stop completed")
        except Exception as e:
            logger.error(f"Error in safe force stop: {e}")
            self.is_stopping = False