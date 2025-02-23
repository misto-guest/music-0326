import time
import datetime
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

    # Time intervals (in seconds)
    NEXT_TRACK_INTERVAL = 300  # Change tracks every 5 minutes
    STARTUP_DELAY = 10  # Delay after starting app


logger = setup_logger(__name__)


class BeatportMusicController(BaseController, PopupMonitorMixin):
    """Controller for Beatport music automation with daily 6-hour playtime limit."""

    def __init__(self, device: u2.Device):
        super().__init__(device)
        PopupMonitorMixin.__init__(self)
        self.package_name = BeatportMusicConfig.PACKAGE_NAME
        self.app_name = BeatportMusicConfig.APP_NAME

        # Time limit config
        self.daily_limit_hours = 6
        self.daily_playtime_seconds = 0
        self.last_start_time = None
        self.is_playing = False
        self.last_day = datetime.datetime.now().day

        # Register for popup monitoring
        self.register_app_for_monitoring("Beatport Music")
        self.start_popup_monitor()

        # Screen settings
        if not self.setup_screen_settings():
            logger.warning("Failed to set up screen settings during initialization")

        # Save rotation state
        self.initial_rotation_state = self.get_rotation_settings()

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.stop_popup_monitor()
            if self.is_playing and self.last_start_time:
                self._update_playtime()
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
            self.device.shell('settings put system screen_off_timeout 1800000')   # 30 min
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
        """Verify rotation is disabled, fix if not."""
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
        """Reset if new day."""
        current_day = datetime.datetime.now().day
        if current_day != self.last_day:
            logger.info(f"New day, resetting playtime from {self.daily_playtime_seconds/3600:.2f}h to 0")
            self.daily_playtime_seconds = 0
            self.last_day = current_day

    def _update_playtime(self) -> None:
        """Add elapsed time to daily total with final session tracking."""
        if self.last_start_time:
            elapsed = (datetime.datetime.now() - self.last_start_time).total_seconds()
            self.daily_playtime_seconds += elapsed
            hours_played = self.daily_playtime_seconds / 3600
            logger.info(
                f"Updated playtime: {hours_played:.2f}h "
                f"(added {elapsed / 60:.2f}min)"
            )
            self.last_start_time = None

    def _start_playtime_tracking(self) -> None:
        """Begin counting time with proper state initialization."""
        self._reset_daily_playtime()  # Reset if it's a new day
        if not self.is_playing:
            self.last_start_time = datetime.datetime.now()
            self.is_playing = True
            logger.info(f"Started playtime tracking at {self.last_start_time.strftime('%H:%M:%S')}")

    def _stop_playtime_tracking(self) -> None:
        """Stop counting time."""
        if self.is_playing:
            self._update_playtime()
            self.is_playing = False
            logger.info(f"Stopped playtime tracking. Total today: {self.daily_playtime_seconds/3600:.2f} hours")

    def check_daily_limit_reached(self) -> bool:
        """Check if 6h daily limit reached with proper tracking."""
        self._reset_daily_playtime()

        if self.is_playing:
            # Update current session time
            self._update_playtime()
            # Restart tracking from now
            self._start_playtime_tracking()

        hours_played = self.daily_playtime_seconds / 3600
        if hours_played >= self.daily_limit_hours:
            logger.warning(
                f"Daily limit reached: {hours_played:.2f} / "
                f"{self.daily_limit_hours}h"
            )
            return True
        else:
            logger.info(
                f"Playtime status: {hours_played:.2f} hours of "
                f"{self.daily_limit_hours} hour daily limit"
            )
            return False

    def handle_isoclipboard(self) -> bool:
        """Not used in Beatport; fallback to handle_initial_setup()."""
        logger.warning("Beatport doesn't use IsoClipboard. Using handle_initial_setup instead.")
        return self.handle_initial_setup()

    def handle_initial_setup(self) -> bool:
        """Full UI setup for Beatport, with forced app restart."""
        try:
            if self.check_daily_limit_reached():
                logger.warning("Can't start Beatport - daily limit reached")
                return False

            logger.info("Performing initial Beatport setup with forced restart...")

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
        """Playback starts after shuffle click, so no extra action needed."""
        logger.info("Playback already initiated via shuffle button. No further action required for Beatport.")
        return True

    def prepare_for_action(self) -> bool:
        """Ensure we can safely interact with app while maintaining playtime."""
        try:
            # Don't check daily limit here, we already handle that in action methods
            if not self.ensure_screen_active():
                logger.error("Failed to ensure screen is active")
                return False

            if self._verify_app_running():
                return True

            # For app restart:
            # 1. Save current state and time
            was_playing = self.is_playing
            self._update_playtime()

            if not self.start_app():
                return False

            time.sleep(1)
            running = self._verify_app_running()

            # 2. Restore state if app was playing
            if running and was_playing:
                self._start_playtime_tracking()

            return running

        except Exception as e:
            logger.error(f"Error preparing for action: {e}")
            return False

    def play_pause(self) -> bool:
        """Toggle play/pause with daily limit checks."""
        if self.is_playing:
            self._stop_playtime_tracking()
        else:
            if self.check_daily_limit_reached():
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
        """Go to next track with playtime preservation."""
        if self.is_playing and self.check_daily_limit_reached():
            logger.warning("Daily limit reached - stopping playback instead of next track")
            return self.play_pause()

        start_time = time.time()
        try:
            logger.info("Attempting next track...")
            prepared = False
            while time.time() - start_time < 15:
                if self.prepare_for_action():  # This updates playtime
                    prepared = True
                    break
                time.sleep(2)

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
        """Minimize (home) or maximize Beatport without affecting playback."""
        try:
            if minimize:
                logger.info("Minimizing Beatport window")
                # Don't change playback state on minimize
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