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
        self.package_name = TidalMusicConfig.PACKAGE_NAME
        self.app_name = TidalMusicConfig.APP_NAME
        self.isoclipboard_package = "com.example.isolatedclipboard"

        # Register apps for monitoring
        self.register_app_for_monitoring("Tidal Music")
        self.register_app_for_monitoring("IsoClipboard")

        # Start popup monitor
        self.start_popup_monitor()

        # Set up screen settings
        if not self.setup_screen_settings():
            logger.warning("Failed to set up screen settings during initialization")

        # Optionally, capture initial rotation state for later restoration (only at session end)
        self.initial_rotation_state = self.get_rotation_settings()

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

    def handle_isoclipboard(self) -> bool:
        """Handle IsoClipboard automation for Tidal."""
        try:
            logger.info(f"Initial rotation settings: {self.get_rotation_settings()}")
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

            if not self._handle_fetch_operation():
                return False

            if self.needs_restart("Tidal Music"):
                logger.info("Restarting Tidal after force-close")
                self.clear_restart_flag("Tidal Music")
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

    def _start_isoclipboard_safely(self) -> bool:
        max_attempts = 3
        for attempt in range(max_attempts):
            logger.info(f"Tidal: Starting IsoClipboard attempt {attempt + 1}/{max_attempts}")

            # Robust steps: unlock screen and press home button
            self.device.shell("input keyevent 82")
            time.sleep(1)
            self.device.shell("input keyevent 3")
            time.sleep(1)

            if not self._verify_rotation_disabled():
                logger.error("Tidal: Rotation control lost before app start")
                continue

            self.device.app_stop(self.isoclipboard_package)
            time.sleep(1)
            self.device.shell(f'am start -W {self.isoclipboard_package}/.MainActivity --activity-single-top')
            time.sleep(3)

            if not self._verify_rotation_disabled():
                logger.error("Tidal: Rotation got enabled during app start")
                continue

            # Poll for confirmation up to 10 iterations (~10 seconds)
            for _ in range(10):
                current_app = self.device.app_current()
                logger.info(f"Tidal: Current app info: {current_app}")
                fetch_button = self.device.xpath(
                    '//*[@resource-id="com.example.isolatedclipboard:id/buttonFetchUrl7"]'
                )
                if current_app.get('package') == self.isoclipboard_package or fetch_button.exists:
                    logger.info("Tidal: IsoClipboard successfully brought to foreground")
                    return True

                logger.warning("Tidal: IsoClipboard not in foreground, retrying...")

                # Retry with robust keyevent steps
                self.device.shell("input keyevent 82")
                time.sleep(1)
                self.device.shell("input keyevent 3")
                time.sleep(1)
                self.device.press("home")
                time.sleep(1)
                self.device.shell(f'am start -W {self.isoclipboard_package}/.MainActivity --activity-single-top')
                time.sleep(2)

            logger.error(f"Tidal: Failed to bring IsoClipboard to foreground on attempt {attempt + 1}")
            time.sleep(2)
        logger.error("Tidal: All attempts to start IsoClipboard safely failed")
        return False

    def _handle_fetch_operation(self) -> bool:
        """Handle the FETCH operation for Tidal."""
        try:
            time.sleep(3)
            if not self._verify_rotation_disabled():
                return False

            fetch_xpath = '//*[@resource-id="com.example.isolatedclipboard:id/buttonFetchUrl7"]'
            fetch_button = self.device.xpath(fetch_xpath)

            if fetch_button.exists:
                time.sleep(2)
                fetch_button.click()
                logger.info("Clicked FETCH Tidal button using XPath")
                time.sleep(8)
            else:
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

    def _ensure_mini_player(self):
        """Ensure the mini-player is visible to maintain correct Tidal state."""
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

    def prepare_for_action(self) -> bool:
        """Streamlined preparation before performing an action."""
        try:
            if not self.ensure_screen_active():
                logger.error("Failed to ensure screen active before action")
                return False

            if self._verify_app_running():
                return True

            if self.needs_restart("Tidal Music"):
                logger.info("Restarting Tidal after force-close")
                self.clear_restart_flag("Tidal Music")
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
            try:
                self.device.shell('input keyevent KEYCODE_MEDIA_PLAY_PAUSE')
                logger.info("Sent play/pause keyevent after error")
                time.sleep(2)
                return True
            except Exception:
                return False

    def next_track(self) -> bool:
        """Skip to next track with a max 15-second wait for Tidal readiness."""
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
                logger.warning("Timed out preparing Tidal; using keyevent fallback for next track")
                self.device.shell('input keyevent KEYCODE_MEDIA_NEXT')
                time.sleep(2)
                return True

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
            try:
                self.device.shell('input keyevent KEYCODE_MEDIA_NEXT')
                time.sleep(2)
                return True
            except Exception:
                return False

    def previous_track(self) -> bool:
        """Go to previous track with a max 15-second wait for Tidal readiness."""
        start_time = time.time()
        try:
            logger.info("Tidal: Attempting previous track...")
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
            prepared = False
            while time.time() - start_time < 15:
                if self.prepare_for_action():
                    prepared = True
                    break
                time.sleep(2)
            if not prepared:
                logger.warning("Timed out preparing Tidal; cannot like song.")
                return False

            like_button = self.device.xpath('//*[@resource-id="com.aspiro.tidal:id/favoriteButton"]')
            if not like_button.exists:
                logger.error("Like button not found in Tidal.")
                return False

            like_button.click()
            logger.info("Clicked like button in Tidal")
            time.sleep(5)
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
        """Stop Tidal app and restore rotation state if desired at session end."""
        try:
            self.device.app_stop(self.package_name)
            time.sleep(1)
            if self.is_running():
                logger.warning("App still running after stop attempt, trying force-stop")
                return self.force_stop()

            if self.initial_rotation_state:
                self._restore_rotation_state(self.initial_rotation_state)
            logger.info("Restored rotation state after stopping Tidal.")
            return True
        except Exception as e:
            logger.error(f"Error stopping Tidal: {e}")
            return False

    def start_app(self) -> bool:
        """Start Tidal app using am start command without restoring rotation immediately."""
        try:
            logger.info("Starting Tidal...")
            if not self._force_disable_rotation():
                return False

            logger.info("Attempting start with am start command...")
            self.device.shell(
                f'am start -W -n {self.package_name}/com.aspiro.wamp.LoginFragmentActivity --activity-single-top'
            )
            time.sleep(2)

            if self._verify_app_running():
                logger.info("Tidal started successfully with am start command")
                return True

            logger.info("am start command did not launch Tidal properly, retrying...")
            time.sleep(1)
            if self._verify_app_running():
                logger.info("Tidal started successfully after retry")
                return True

            logger.error("Failed to start Tidal")
            return False

        except Exception as e:
            logger.error(f"Error starting Tidal: {e}")
            return False

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
                    command = f"monkey -p {self.package_name} -c android.intent.category.LAUNCHER 1"
                    self.device.shell(command)
                    time.sleep(3)
                    return True
                else:
                    return self.start_app()
        except Exception as e:
            logger.error(f"Failed to manage window state: {e}")
            return False