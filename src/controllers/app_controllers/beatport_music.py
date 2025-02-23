# src/controllers/app_controllers/beatport_music.py

import time
import datetime
from typing import Dict
import uiautomator2 as u2
from src.controllers.base_controller import BaseController
from src.controllers.mixins.popup_monitor import PopupMonitorMixin
from src.utils.logging_utils import setup_logger


# Define Beatport configuration here
class BeatportMusicConfig:
    """Configuration for Beatport Music app."""

    # App identification
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
        """Initialize Beatport music controller with daily time limit."""
        super().__init__(device)
        PopupMonitorMixin.__init__(self)
        self.package_name = BeatportMusicConfig.PACKAGE_NAME
        self.app_name = BeatportMusicConfig.APP_NAME

        # Time tracking for daily limit
        self.daily_limit_hours = 6
        self.daily_playtime_seconds = 0
        self.last_start_time = None
        self.is_playing = False
        self.last_day = datetime.datetime.now().day

        # Register app for monitoring
        self.register_app_for_monitoring("Beatport Music")

        # Start popup monitor
        self.start_popup_monitor()

        # Set up screen settings
        if not self.setup_screen_settings():
            logger.warning("Failed to set up screen settings during initialization")

        # Save initial rotation state for later restoration
        self.initial_rotation_state = self.get_rotation_settings()

    def __del__(self):
        """Cleanup when controller is deleted."""
        try:
            self.stop_popup_monitor()
            # Stop tracking playtime if still active
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
        """Setup screen timeout and stay-on settings."""
        try:
            logger.info("Setting up screen settings")
            self.device.shell('settings put system screen_off_timeout 1800000')
            self.device.shell('settings put global stay_on_while_plugged_in 3')
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
        """Restore rotation to initial state (used only at session end)."""
        try:
            if 'auto_rotate' in initial_state:
                self.device.shell(f'settings put system accelerometer_rotation {initial_state["auto_rotate"]}')
            if 'user_rotation' in initial_state:
                self.device.shell(f'settings put system user_rotation {initial_state["user_rotation"]}')
            logger.info("Restored initial rotation state")
        except Exception as e:
            logger.error(f"Error restoring rotation state: {e}")

    def ensure_screen_active(self) -> bool:
        """Ensure device screen is active."""
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
        """Reset daily playtime tracking if day has changed."""
        current_day = datetime.datetime.now().day
        if current_day != self.last_day:
            logger.info(
                f"New day detected, resetting playtime tracking from {self.daily_playtime_seconds / 3600:.2f} hours to 0")
            self.daily_playtime_seconds = 0
            self.last_day = current_day

    def _update_playtime(self) -> None:
        """Update the tracked playtime."""
        if self.last_start_time:
            elapsed = (datetime.datetime.now() - self.last_start_time).total_seconds()
            self.daily_playtime_seconds += elapsed
            logger.info(
                f"Updated playtime: {self.daily_playtime_seconds / 3600:.2f} hours (added {elapsed / 60:.2f} minutes)")
            self.last_start_time = None

    def _start_playtime_tracking(self) -> None:
        """Start tracking playtime."""
        self._reset_daily_playtime()
        if not self.is_playing:
            self.last_start_time = datetime.datetime.now()
            self.is_playing = True
            logger.info(f"Started playtime tracking at {self.last_start_time.strftime('%H:%M:%S')}")

    def _stop_playtime_tracking(self) -> None:
        """Stop tracking playtime and update the total."""
        if self.is_playing:
            self._update_playtime()
            self.is_playing = False
            logger.info(f"Stopped playtime tracking. Total today: {self.daily_playtime_seconds / 3600:.2f} hours")

    def check_daily_limit_reached(self) -> bool:
        """Check if daily playtime limit has been reached."""
        self._reset_daily_playtime()
        if self.is_playing:
            self._update_playtime()
            self._start_playtime_tracking()  # Restart tracking from now

        hours_played = self.daily_playtime_seconds / 3600
        limit_reached = hours_played >= self.daily_limit_hours

        if limit_reached:
            logger.warning(
                f"Daily playtime limit reached: {hours_played:.2f} hours played out of {self.daily_limit_hours} hour limit")
        else:
            logger.info(f"Playtime status: {hours_played:.2f} hours of {self.daily_limit_hours} hour daily limit")

        return limit_reached

    def handle_isoclipboard(self) -> bool:
        """
        Implement required method from base class.
        Beatport doesn't use IsoClipboard - use handle_initial_setup instead.
        """
        logger.warning("Beatport doesn't use IsoClipboard functionality. Use handle_initial_setup instead.")
        # If we really want to provide similar functionality, call our setup method
        return self.handle_initial_setup()

    def handle_initial_setup(self) -> bool:
        """Perform initial setup for Beatport using a forced restart."""
        try:
            # Check if we've hit the daily playtime limit
            if self.check_daily_limit_reached():
                logger.warning("Can't start Beatport - daily playtime limit reached")
                return False

            logger.info("Performing initial Beatport setup with forced restart...")

            # Disable rotation to ensure a consistent UI
            if not self._force_disable_rotation():
                logger.error("Failed to disable rotation")
                return False

            # Force restart Beatport to get it into the expected initial state
            if not self.restart_app():
                logger.error("Failed to restart Beatport")
                return False

            # Wait for the app to load
            time.sleep(BeatportMusicConfig.STARTUP_DELAY)

            # Perform the initial UI sequence (click main graph, library graph, etc.)
            if not self._perform_initial_setup():
                logger.error("Initial Beatport UI setup failed")
                return False

            # Start playback using the shuffle/play logic
            if not self._handle_shuffle_and_play():
                logger.error("Failed to start Beatport playback")
                return False

            # Begin tracking playtime
            self._start_playtime_tracking()

            logger.info("Beatport initial setup completed successfully")
            return True

        except Exception as e:
            logger.error(f"Error during Beatport initial setup: {e}")
            return False

    def _perform_initial_setup(self) -> bool:
        """Perform the initial UI sequence for Beatport."""
        try:
            logger.info("Performing Beatport initial UI sequence...")

            # Step 1: Click main graph
            main_graph = self.device(resourceId="com.beatport.mobile:id/main_graph")
            if main_graph.exists:
                main_graph.click()
                logger.info("Clicked main graph")
            else:
                logger.error("Main graph element not found")
                return False
            time.sleep(2)

            # Step 2: Click library graph
            library_graph = self.device(resourceId="com.beatport.mobile:id/library_graph")
            if library_graph.exists:
                library_graph.click()
                logger.info("Clicked library graph")
            else:
                logger.error("Library graph element not found")
                return False
            time.sleep(3)

            # Step 3: Click playlist item
            playlist_item = self.device(resourceId="com.beatport.mobile:id/constraintLayoutPlaylistItem")
            if playlist_item.exists:
                playlist_item.click()
                logger.info("Clicked playlist item")
            else:
                logger.error("Playlist item element not found")
                return False
            time.sleep(3)

            # Step 4: Click shuffle button
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
            logger.error(f"Error in Beatport initial UI sequence: {e}")
            return False

    def _handle_shuffle_and_play(self) -> bool:
        """Start playback in Beatport."""
        try:
            logger.info("Looking for Beatport playback controls...")

            # Try to find and click play/shuffle button with multiple attempts
            for attempt in range(3):
                # Try most common buttons
                play_button = self.device(resourceId=f"{self.package_name}:id/linearLayoutPlay")
                shuffle_button = self.device(resourceId=f"{self.package_name}:id/linearLayoutShuffle")
                play_all_button = self.device(text="Play All")
                shuffle_all_button = self.device(text="Shuffle All")

                # Try UI navigation if needed
                if attempt > 0:
                    logger.info(f"Play button not found, trying alternative navigation (attempt {attempt + 1})")
                    # Try to navigate to library or playlists section
                    library_tab = self.device(resourceId=f"{self.package_name}:id/libraryTab")
                    if library_tab.exists:
                        library_tab.click()
                        logger.info("Clicked library tab")
                        time.sleep(2)

                    # Try to find playlists
                    playlists_button = self.device(text="Playlists")
                    if playlists_button.exists:
                        playlists_button.click()
                        logger.info("Clicked playlists button")
                        time.sleep(2)

                # Check again for play buttons
                if play_button.exists:
                    play_button.click()
                    logger.info("Clicked Beatport play button")
                    time.sleep(3)
                    return True
                elif shuffle_button.exists:
                    shuffle_button.click()
                    logger.info("Clicked Beatport shuffle button")
                    time.sleep(3)
                    return True
                elif play_all_button.exists:
                    play_all_button.click()
                    logger.info("Clicked 'Play All' button")
                    time.sleep(3)
                    return True
                elif shuffle_all_button.exists:
                    shuffle_all_button.click()
                    logger.info("Clicked 'Shuffle All' button")
                    time.sleep(3)
                    return True

                # Wait before next attempt
                time.sleep(2)

            # If we couldn't find play buttons, try media key as fallback
            logger.warning("No Beatport playback controls found, using media key fallback")
            self.device.shell('input keyevent KEYCODE_MEDIA_PLAY')
            time.sleep(1)

            # We'll try our best - consider this successful even if we couldn't find the buttons
            return True

        except Exception as e:
            logger.error(f"Error starting Beatport playback: {e}")
            # Try media key fallback
            try:
                self.device.shell('input keyevent KEYCODE_MEDIA_PLAY')
                logger.info("Sent media play key as fallback")
                time.sleep(1)
                return True
            except:
                return False

    def prepare_for_action(self) -> bool:
        """Streamlined preparation before performing an action."""
        try:
            # Check daily limit first
            if self.check_daily_limit_reached():
                logger.warning("Daily playtime limit reached - cannot prepare for action")
                return False

            if not self.ensure_screen_active():
                logger.error("Failed to ensure screen active before action")
                return False

            if self._verify_app_running():
                return True

            if self.needs_restart("Beatport Music"):
                logger.info("Restarting Beatport after force-close")
                self.clear_restart_flag("Beatport Music")
                time.sleep(1)

            if not self.start_app():
                return False

            time.sleep(1)
            return self._verify_app_running()
        except Exception as e:
            logger.error(f"Error preparing for action: {e}")
            return False

    def play_pause(self) -> bool:
        """Toggle play/pause with daily limit enforcement."""
        # First check if we're about to exceed daily limit
        if self.is_playing:
            # When pausing, no need to check limit
            self._stop_playtime_tracking()
        else:
            # Only check limit when trying to play
            if self.check_daily_limit_reached():
                logger.warning("Cannot start playback - daily limit reached")
                return False

        start_time = time.time()
        try:
            logger.info("Attempting play/pause...")
            prepared = False
            while time.time() - start_time < 15:
                if self.prepare_for_action():
                    prepared = True
                    break
                time.sleep(2)
            if not prepared:
                logger.warning("Timed out preparing Beatport; using keyevent fallback.")
                self.device.shell('input keyevent KEYCODE_MEDIA_PLAY_PAUSE')

                # If we were playing, we're now paused
                if self.is_playing:
                    self._stop_playtime_tracking()
                else:
                    self._start_playtime_tracking()

                return True

            # Try to find and click the play/pause button
            play_button = self.device(resourceId=f"{self.package_name}:id/playPauseButton")
            if play_button.exists:
                play_button.click()
                logger.info("Clicked Beatport play/pause button")

                # Update tracking
                if self.is_playing:
                    self._stop_playtime_tracking()
                else:
                    self._start_playtime_tracking()

                time.sleep(1)
                return True

            logger.info("Play button not found, using keyevent fallback")
            self.device.shell('input keyevent KEYCODE_MEDIA_PLAY_PAUSE')

            # Update tracking
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

                # Update tracking
                if self.is_playing:
                    self._stop_playtime_tracking()
                else:
                    self._start_playtime_tracking()

                logger.info("Sent play/pause keyevent after error")
                time.sleep(1)
                return True
            except Exception:
                return False

    def next_track(self) -> bool:
        """Skip to next track with a max 15-second wait for Beatport readiness."""
        # Check if playing and if daily limit reached
        if self.is_playing and self.check_daily_limit_reached():
            logger.warning("Daily playtime limit reached - stopping playback instead of next track")
            return self.play_pause()  # Stop playback instead

        start_time = time.time()
        try:
            logger.info("Attempting next track...")
            prepared = False
            while time.time() - start_time < 15:
                if self.prepare_for_action():
                    prepared = True
                    break
                time.sleep(2)
            if not prepared:
                logger.warning("Timed out preparing Beatport; using keyevent fallback for next track")
                self.device.shell('input keyevent KEYCODE_MEDIA_NEXT')
                time.sleep(1)
                return True

            next_button = self.device(resourceId=f"{self.package_name}:id/nextButton")
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
            logger.error(f"Error skipping to next track: {e}")
            try:
                self.device.shell('input keyevent KEYCODE_MEDIA_NEXT')
                time.sleep(1)
                return True
            except Exception:
                return False

    def previous_track(self) -> bool:
        """Go to previous track with a max 15-second wait for Beatport readiness."""
        # Check if playing and if daily limit reached
        if self.is_playing and self.check_daily_limit_reached():
            logger.warning("Daily playtime limit reached - stopping playback instead of previous track")
            return self.play_pause()  # Stop playback instead

        start_time = time.time()
        try:
            logger.info("Beatport: Attempting previous track...")
            prepared = False
            while time.time() - start_time < 15:
                if self.prepare_for_action():
                    prepared = True
                    break
                time.sleep(2)
            if not prepared:
                logger.warning("Beatport: Timed out preparing; using keyevent fallback for previous track")
                self.device.shell('input keyevent KEYCODE_MEDIA_PREVIOUS')
                time.sleep(1)
                return True

            prev_button = self.device(resourceId=f"{self.package_name}:id/previousButton")
            if prev_button.exists:
                prev_button.click()
                logger.info("Beatport: Clicked previous track button")
                time.sleep(1)
                return True

            logger.info("Beatport: UI previous button not found; using keyevent fallback")
            self.device.shell('input keyevent KEYCODE_MEDIA_PREVIOUS')
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Beatport: Error going to previous track: {e}")
            try:
                self.device.shell('input keyevent KEYCODE_MEDIA_PREVIOUS')
                time.sleep(1)
                return True
            except Exception as ex:
                logger.error(f"Beatport: Fallback keyevent failed: {ex}")
                return False

    def like_current_song(self) -> bool:
        """Like current song with a max 15-second wait for Beatport readiness."""
        # Check if playing and if daily limit reached
        if self.is_playing and self.check_daily_limit_reached():
            logger.warning("Daily playtime limit reached - stopping playback instead of liking song")
            return self.play_pause()  # Stop playback instead

        start_time = time.time()
        try:
            logger.info("Starting like song action...")
            prepared = False
            while time.time() - start_time < 15:
                if self.prepare_for_action():
                    prepared = True
                    break
                time.sleep(2)
            if not prepared:
                logger.warning("Timed out preparing Beatport; cannot like song.")
                return False

            like_button = self.device(resourceId=f"{self.package_name}:id/favoriteButton")
            if not like_button.exists:
                # Try alternative like button
                like_button = self.device(resourceId=f"{self.package_name}:id/likeButton")
                if not like_button.exists:
                    logger.error("Like button not found in Beatport.")
                    return False

            like_button.click()
            logger.info("Clicked like button in Beatport")
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Error liking current song: {e}")
            return False

    def _verify_app_running(self) -> bool:
        """Optimized verification of Beatport running state."""
        try:
            if self.device(packageName=self.package_name).exists:
                logger.info("Found Beatport UI elements")
                return True

            current_app = self.device.app_current()
            if current_app.get('package') == self.package_name:
                logger.info("Beatport is current app")
                return True

            if self.package_name in self.device.shell('dumpsys activity activities | grep -i "mResumedActivity"'):
                logger.info("Beatport found in resumed activities")
                return True

            return False
        except Exception as e:
            logger.error(f"Error verifying app state: {e}")
            return False

    def stop_app(self) -> bool:
        """Stop Beatport app and clean up playtime tracking."""
        try:
            # Stop playtime tracking if active
            if self.is_playing:
                self._stop_playtime_tracking()

            self.device.app_stop(self.package_name)
            time.sleep(1)
            if self.is_running():
                logger.warning("App still running after stop attempt, trying force-stop")
                return self.force_stop()

            if self.initial_rotation_state:
                self._restore_rotation_state(self.initial_rotation_state)
            logger.info("Restored rotation state after stopping Beatport.")
            return True
        except Exception as e:
            logger.error(f"Error stopping Beatport: {e}")
            return False

    def start_app(self) -> bool:
        """Start Beatport app if within daily limit."""
        # Check if we would exceed daily limit
        if self.check_daily_limit_reached():
            logger.warning("Cannot start Beatport - daily limit reached")
            return False

        try:
            logger.info("Starting Beatport...")
            if not self._force_disable_rotation():
                return False

            logger.info("Attempting start with am start command...")
            self.device.shell(
                f'am start -W -n {self.package_name}/{BeatportMusicConfig.MAIN_ACTIVITY} --activity-single-top'
            )
            time.sleep(3)

            if self._verify_app_running():
                logger.info("Beatport started successfully with am start command")
                return True

            logger.info("am start command did not launch Beatport properly, retrying...")
            time.sleep(1)
            if self._verify_app_running():
                logger.info("Beatport started successfully after retry")
                return True

            logger.error("Failed to start Beatport")
            return False

        except Exception as e:
            logger.error(f"Error starting Beatport: {e}")
            return False

    def is_running(self) -> bool:
        """Check if Beatport is running with improved detection."""
        try:
            return self._verify_app_running()
        except Exception as e:
            logger.error(f"Error checking if Beatport is running: {e}")
            return False

    def force_stop(self) -> bool:
        """Force stop Beatport."""
        try:
            self.device.app_stop(self.package_name)
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error force stopping Beatport: {e}")
            return False

    def manage_window_state(self, minimize: bool = True) -> bool:
        """Manage Beatport window state."""
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
        """Force stop and restart Beatport to ensure initial UI state."""
        try:
            # Force-stop the Beatport app
            self.device.app_stop(BeatportMusicConfig.PACKAGE_NAME)
            time.sleep(2)  # Wait a moment to ensure it closes
            start_command = f"am start -W -n {BeatportMusicConfig.PACKAGE_NAME}/{BeatportMusicConfig.MAIN_ACTIVITY} --activity-single-top"
            self.device.shell(start_command)
            time.sleep(3)  # Allow time for the app to load
            if self._verify_app_running():
                logger.info("Beatport restarted successfully.")
                return True
            else:
                logger.error("Beatport failed to restart.")
                return False
        except Exception as e:
            logger.error(f"Error restarting Beatport: {e}")
            return False