# src/controllers/app_controllers/tidal_music.py

import time
from typing import Dict
import uiautomator2 as u2
from src.controllers.base_controller import BaseController
from src.controllers.mixins.popup_monitor import PopupMonitorMixin
from src.constants.app_configs import TidalMusicConfig
from src.utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class TidalMusicController(BaseController, PopupMonitorMixin):
    """Controller for Tidal Music automation."""

    def __init__(self, device: u2.Device):
        """Initialize Tidal Music controller."""
        super().__init__(device)
        PopupMonitorMixin.__init__(self)
        self.package_name = TidalMusicConfig.PACKAGE_NAME  # Typically 'com.aspiro.tidal'
        self.app_name = TidalMusicConfig.APP_NAME
        self.isoclipboard_package = "com.example.isolatedclipboard"

        # Register apps for monitoring
        self.register_app_for_monitoring("Tidal")
        self.register_app_for_monitoring("IsoClipboard")

        # Start popup monitor
        self.start_popup_monitor()

        # Set up screen settings
        if not self.setup_screen_settings():
            logger.warning("Failed to set up screen settings during initialization")

    def __del__(self):
        """Cleanup when controller is deleted."""
        try:
            self.stop_popup_monitor()
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")

    def get_rotation_settings(self) -> Dict[str, str]:
        """Get current rotation settings."""
        try:
            auto_rotate = self.device.shell('settings get system accelerometer_rotation').output.strip()
            user_rotation = self.device.shell('settings get system user_rotation').output.strip()
            return {
                'auto_rotate': auto_rotate,
                'user_rotation': user_rotation
            }
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

    def handle_isoclipboard(self) -> bool:
        """Handle IsoClipboard automation."""
        initial_rotation_state = None
        try:
            initial_rotation_state = self.get_rotation_settings()
            logger.info(f"Initial rotation settings: {initial_rotation_state}")

            if not self._force_disable_rotation():
                logger.error("Failed to disable rotation")
                return False

            if not self._start_isoclipboard_safely():
                if self.needs_restart("IsoClipboard"):
                    logger.info("Retrying IsoClipboard after force-close")
                    self.clear_restart_flag("IsoClipboard")
                    time.sleep(2)
                    if not self._start_isoclipboard_safely():
                        return False
                else:
                    return False

            # Handle fetch operation
            if not self._handle_fetch_operation():
                return False

            # Check for Tidal restart
            if self.needs_restart("Tidal"):
                logger.info("Restarting Tidal after force-close")
                self.clear_restart_flag("Tidal")
                time.sleep(2)
                if not self.prepare_for_action():
                    return False

            if not self._handle_shuffle_and_play():
                return False

            self._ensure_mini_player()
            time.sleep(2)

            self.device.press("home")
            time.sleep(1)
            return True

        except Exception as e:
            logger.error(f"Error with IsoClipboard: {e}")
            return False
        finally:
            if initial_rotation_state:
                self._restore_rotation_state(initial_rotation_state)

    def _ensure_mini_player(self):
        try:
            logger.info("Searching for mini_player element...")
            mini_player = self.device.xpath('//*[@resource-id="com.aspiro.tidal:id/miniControlsView"]')
            if mini_player.exists:
                mini_player.click()
                logger.info("Clicked mini_player to ensure correct Tidal state")
                time.sleep(1)
            else:
                logger.info("mini_player element not found")
        except Exception as e:
            logger.error(f"Error ensuring mini_player state: {e}")

    def _start_isoclipboard_safely(self) -> bool:
        """Start IsoClipboard app with improved timing and safety checks."""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logger.info(f"Starting IsoClipboard attempt {attempt + 1}/{max_attempts}")

                # Verify rotation is disabled
                if not self._verify_rotation_disabled():
                    logger.error("Rotation control lost before app start")
                    continue

                # Close existing instance if running
                self.device.app_stop(self.isoclipboard_package)
                time.sleep(3)

                # Start app using activity manager
                self.device.shell(
                    f'am start -W {self.isoclipboard_package}/.MainActivity --activity-single-top'
                )
                time.sleep(5)  # Increased pause after starting app

                # Verify rotation is still disabled
                if not self._verify_rotation_disabled():
                    logger.error("Rotation got enabled during app start")
                    continue

                for check in range(3):
                    current_app = self.device.app_current()
                    if current_app.get('package') == self.isoclipboard_package:
                        logger.info("IsoClipboard successfully brought to foreground")
                        time.sleep(2)
                        return True
                    logger.warning(f"IsoClipboard not in foreground (check {check + 1}/3), retrying...")
                    self.device.press("home")
                    time.sleep(2)
                    self.device.shell(
                        f'am start -W {self.isoclipboard_package}/.MainActivity --activity-single-top'
                    )
                    time.sleep(3)
                logger.error(f"Failed to bring IsoClipboard to foreground on attempt {attempt + 1}")
            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}: {e}")
            time.sleep(3)
        logger.error("All attempts to start IsoClipboard safely failed")
        return False

    def _handle_fetch_operation(self) -> bool:
        """Handle the FETCH button operation for Tidal with improved timing."""
        try:
            time.sleep(3)
            # Verify rotation before fetch
            if not self._verify_rotation_disabled():
                return False

            # Click FETCH button for Tidal (assuming buttonFetchUrl4 for Tidal)
            fetch_xpath = '//*[@resource-id="com.example.isolatedclipboard:id/buttonFetchUrl7"]'
            fetch_button = self.device.xpath(fetch_xpath)

            if fetch_button.exists:
                time.sleep(2)
                fetch_button.click()
                logger.info("Clicked FETCH Tidal button using XPath")
                time.sleep(8)
            else:
                # Fallback to resourceId if XPath fails
                fetch_button = self.device(resourceId="com.example.isolatedclipboard:id/buttonFetchUrl7")
                if not fetch_button.exists:
                    logger.error("FETCH Tidal button not found")
                    return False
                time.sleep(2)
                fetch_button.click()
                logger.info("Clicked FETCH Tidal button using resourceId")
                time.sleep(8)

            return True
        except Exception as e:
            logger.error(f"Error in fetch operation: {e}")
            return False

    def _handle_shuffle_and_play(self) -> bool:
        """Handle shuffle button interaction for Tidal."""
        try:
            if not self._verify_rotation_disabled():
                return False

            time.sleep(5)
            logger.info("Looking for Tidal shuffle button...")

            # Tidal-specific shuffle button ID
            shuffle_button = self.device.xpath('//*[@resource-id="com.aspiro.tidal:id/playbackControlButtonSecond"]')
            if not shuffle_button.exists:
                logger.error("Tidal shuffle button not found")
                return False

            shuffle_button.click()
            logger.info("Clicked Tidal shuffle button")
            time.sleep(5)
            return True

        except Exception as e:
            logger.error(f"Error handling shuffle: {e}")
            return False

    def prepare_for_action(self) -> bool:
        """Streamlined preparation for actions."""
        try:
            if not self.ensure_screen_active():
                logger.error("Failed to ensure screen active before action")
                return False

            if self._verify_app_running():
                return True

            if self.needs_restart("Tidal"):
                logger.info("Restarting Tidal after force-close")
                self.clear_restart_flag("Tidal")
                time.sleep(1)

            if not self.start_app():
                return False

            time.sleep(1)
            return self._verify_app_running()

        except Exception as e:
            logger.error(f"Error preparing for action: {e}")
            return False

    def play_pause(self) -> bool:
        """Toggle play/pause with a max 15-second wait for Tidal readiness."""
        start_time = time.time()
        try:
            logger.info("Attempting play/pause...")
            # 1. Wait up to 15s for Tidal readiness.
            prepared = False
            while time.time() - start_time < 15:
                if self.prepare_for_action():
                    prepared = True
                    break
                time.sleep(2)

            if not prepared:
                logger.warning("Timed out preparing Tidal; using keyevent fallback.")
                self.device.shell('input keyevent KEYCODE_MEDIA_PLAY_PAUSE')
                return True

            # 2. If prepared, try the actual UI approach:
            play_button = self.device.xpath('//*[@resource-id="com.aspiro.tidal:id/miniControlsView"]')
            if play_button.exists:
                play_button.click()
                logger.info("Clicked Tidal play/pause button")
                time.sleep(2)
                return True

            logger.info("Play button not found, using keyevent fallback")
            self.device.shell('input keyevent KEYCODE_MEDIA_PLAY_PAUSE')
            time.sleep(2)
            return True

        except Exception as e:
            logger.error(f"Error toggling play/pause: {e}")
            # Final fallback
            try:
                self.device.shell('input keyevent KEYCODE_MEDIA_PLAY_PAUSE')
                logger.info("Sent play/pause keyevent after error")
                time.sleep(2)
                return True
            except:
                return False

    def next_track(self) -> bool:
        """Skip to next track with a max 15-second wait for Tidal readiness."""
        start_time = time.time()
        try:
            logger.info("Attempting next track...")
            # 1. Wait up to 15s for readiness.
            prepared = False
            while time.time() - start_time < 15:
                if self.prepare_for_action():
                    prepared = True
                    break
                time.sleep(2)

            if not prepared:
                logger.warning("Timed out preparing Tidal; using keyevent fallback for next track")
                self.device.shell('input keyevent KEYCODE_MEDIA_NEXT')
                time.sleep(2)
                return True

            # 2. If prepared, try the UI next button.
            next_button = self.device.xpath('//*[@resource-id="com.aspiro.tidal:id/next"]')
            if next_button.exists:
                next_button.click()
                logger.info("Clicked next track button")
                time.sleep(2)
                return True

            logger.info("Next button not found, using keyevent fallback")
            self.device.shell('input keyevent KEYCODE_MEDIA_NEXT')
            time.sleep(2)
            return True

        except Exception as e:
            logger.error(f"Error skipping to next track: {e}")
            # Final fallback
            try:
                self.device.shell('input keyevent KEYCODE_MEDIA_NEXT')
                time.sleep(2)
                return True
            except:
                return False

    def previous_track(self) -> bool:
        """Go to previous track with a max 15-second wait for Tidal readiness."""
        start_time = time.time()
        try:
            logger.info("Tidal: Attempting previous track...")
            # Wait up to 15s for Tidal to be ready.
            prepared = False
            while time.time() - start_time < 15:
                if self.prepare_for_action():
                    prepared = True
                    break
                time.sleep(2)

            if not prepared:
                logger.warning("Tidal: Timed out preparing; using keyevent fallback for previous track")
                self.device.shell('input keyevent KEYCODE_MEDIA_PREVIOUS')
                time.sleep(2)
                return True

            # Try the UI previous button.
            prev_button = self.device.xpath('//*[@resource-id="com.aspiro.tidal:id/previous"]')
            if prev_button.exists:
                prev_button.click()
                logger.info("Tidal: Clicked previous track button")
                time.sleep(2)
                return True

            logger.info("Tidal: UI previous button not found; using keyevent fallback")
            self.device.shell('input keyevent KEYCODE_MEDIA_PREVIOUS')
            time.sleep(2)
            return True

        except Exception as e:
            logger.error(f"Tidal: Error going to previous track: {e}")
            try:
                self.device.shell('input keyevent KEYCODE_MEDIA_PREVIOUS')
                time.sleep(2)
                return True
            except Exception as ex:
                logger.error(f"Tidal: Fallback keyevent failed: {ex}")
                return False

    def like_current_song(self) -> bool:
        """Like current song with a max 15-second wait for Tidal readiness."""
        start_time = time.time()
        try:
            logger.info("Starting like song action...")
            # 1. Wait up to 15s for readiness.
            prepared = False
            while time.time() - start_time < 15:
                if self.prepare_for_action():
                    prepared = True
                    break
                time.sleep(2)

            if not prepared:
                logger.warning("Timed out preparing Tidal; cannot like song.")
                return False

            # 2. Try to click the 'like' button if it exists.
            # Note: Tidal-specific resource ID for the like button
            like_button = self.device.xpath('//*[@resource-id="com.aspiro.tidal:id/favoriteButton"]')
            if not like_button.exists:
                logger.error("Like button not found in Tidal.")
                return False

            like_button.click()
            logger.info("Clicked like button in Tidal")
            time.sleep(2)
            return True

        except Exception as e:
            logger.error(f"Error liking current song: {e}")
            return False

    def _verify_app_running(self) -> bool:
        """Optimized verification of Tidal running state."""
        try:
            if self.device(packageName=self.package_name).exists:
                logger.info("Found Tidal UI elements")
                return True

            current_app = self.device.app_current()
            if current_app.get('package') == self.package_name:
                logger.info("Tidal is current app")
                return True

            if self.package_name in self.device.shell('dumpsys activity activities | grep -i "mResumedActivity"'):
                logger.info("Tidal found in resumed activities")
                return True

            return False

        except Exception as e:
            logger.error(f"Error verifying app state: {e}")
            return False

    def stop_app(self) -> bool:
        """Stop Tidal app."""
        try:
            self.device.app_stop(self.package_name)
            time.sleep(1)
            # Verify app is actually stopped
            if self.is_running():
                logger.warning("App still running after stop attempt, trying force-stop")
                return self.force_stop()
            return True
        except Exception as e:
            logger.error(f"Error stopping Tidal: {e}")
            return False

    def start_app(self) -> bool:
        """Start Tidal app with optimized timing."""
        initial_state = None
        try:
            logger.info("Starting Tidal...")
            initial_state = self.get_rotation_settings()

            # Force disable rotation first
            if not self._force_disable_rotation():
                return False

            logger.info("Attempting start with monkey command...")
            self.device.shell(
                f'monkey -p {self.package_name} -c android.intent.category.LAUNCHER 1'
            )
            time.sleep(2)

            # Quick check
            if self._verify_app_running():
                logger.info("Tidal started successfully with monkey command")
                return True

            # Fallback to activity manager if monkey fails
            logger.info("Monkey command failed, trying activity manager...")
            self.device.shell(
                f'am start -W -n {self.package_name}/com.aspiro.tidal.MainActivity --activity-single-top'
            )
            time.sleep(2)

            # One retry with shorter interval
            if not self._verify_app_running():
                time.sleep(1)
                if self._verify_app_running():
                    logger.info("Tidal started successfully after retry")
                    return True
                logger.error("Failed to start Tidal")
                return False

            logger.info("Tidal started successfully")
            return True

        except Exception as e:
            logger.error(f"Error starting Tidal: {e}")
            return False
        finally:
            if initial_state:
                self._restore_rotation_state(initial_state)

    def is_running(self) -> bool:
        """Check if Tidal is running with improved detection."""
        try:
            return self._verify_app_running()
        except Exception as e:
            logger.error(f"Error checking if Tidal is running: {e}")
            return False

    def force_stop(self) -> bool:
        """Force stop Tidal."""
        try:
            self.device.app_stop(self.package_name)
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error force stopping Tidal: {e}")
            return False

    def manage_window_state(self, minimize: bool = True) -> bool:
        """Manage Tidal window state."""
        try:
            if minimize:
                logger.info("Minimizing Tidal window")
                self.device.press("home")
                time.sleep(1)
                return True
            else:
                logger.info("Maximizing Tidal window")
                if self.is_running():
                    # Use monkey command for more reliable app switching
                    command = (
                        f"monkey -p {self.package_name} -c android.intent.category.LAUNCHER 1"
                    )
                    self.device.shell(command)
                    time.sleep(3)
                    return True
                else:
                    return self.start_app()
        except Exception as e:
            logger.error(f"Failed to manage window state: {e}")
            return False