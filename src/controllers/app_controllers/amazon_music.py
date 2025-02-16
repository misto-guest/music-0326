# src/controllers/app_controllers/amazon_music.py

import time
from typing import Dict
import uiautomator2 as u2
from src.controllers.base_controller import BaseController
from src.controllers.mixins.popup_monitor import PopupMonitorMixin
from src.constants.app_configs import AmazonMusicConfig
from src.utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class AmazonMusicController(BaseController, PopupMonitorMixin):
    """Controller for Amazon Music automation."""

    def __init__(self, device: u2.Device):
        """Initialize Amazon Music controller."""
        super().__init__(device)
        PopupMonitorMixin.__init__(self)
        self.package_name = AmazonMusicConfig.PACKAGE_NAME
        self.app_name = AmazonMusicConfig.APP_NAME
        self.isoclipboard_package = "com.example.isolatedclipboard"

        # Register apps for monitoring
        self.register_app_for_monitoring("Amazon Music")
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

    def check_internet_connection(self, max_retries: int = 5, delay: int = 2) -> bool:
        """Check internet connection using netstat."""
        for attempt in range(max_retries):
            try:
                netstat_check = self.device.shell('netstat -n | grep ESTABLISHED | grep -E "^tcp6.*::ffff:|^tcp[^6]"')
                if getattr(netstat_check, 'exit_code', 0) != 0:
                    logger.warning(f"Failed to get TCP connections (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue

                output = str(getattr(netstat_check, 'output', netstat_check)).strip()
                if not output:
                    logger.warning(f"No TCP connections found (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue

                connections = output.split('\n')
                logger.info(f"Found {len(connections)} TCP connections")
                return True
            except Exception as e:
                logger.error(f"Error checking internet connection: {e}")
                time.sleep(delay)
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

            # Check for Amazon Music restart
            if self.needs_restart("Amazon Music"):
                logger.info("Restarting Amazon Music after force-close")
                self.clear_restart_flag("Amazon Music")
                time.sleep(2)
                if not self.prepare_for_action():
                    return False

            if not self._handle_shuffle_and_play():
                return False

            self.device.press("home")
            time.sleep(1)

            return True
        except Exception as e:
            logger.error(f"Error with IsoClipboard: {e}")
            return False
        finally:
            if initial_rotation_state:
                self._restore_rotation_state(initial_rotation_state)

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
        """Handle the FETCH button operation with improved timing."""
        try:
            time.sleep(3)

            # Verify rotation before fetch
            if not self._verify_rotation_disabled():
                return False

            # Click FETCH button for Amazon Music (buttonFetchUrl3)
            fetch_xpath = '//*[@resource-id="com.example.isolatedclipboard:id/buttonFetchUrl3"]'
            fetch_button = self.device.xpath(fetch_xpath)

            if fetch_button.exists:
                time.sleep(2)
                fetch_button.click()
                logger.info("Clicked FETCH AM button using XPath")
                time.sleep(8)
            else:
                # Fallback to resourceId if XPath fails
                fetch_button = self.device(resourceId="com.example.isolatedclipboard:id/buttonFetchUrl3")
                if not fetch_button.exists:
                    logger.error("FETCH AM button not found")
                    return False

                time.sleep(2)
                fetch_button.click()
                logger.info("Clicked FETCH AM button using resourceId")
                time.sleep(8)

            for attempt in range(3):
                if self.check_internet_connection():
                    return True
                time.sleep(3)

            logger.error("No internet connection available after multiple attempts")
            return False
        except Exception as e:
            logger.error(f"Error in fetch operation: {e}")
            return False

    def _handle_shuffle_and_play(self) -> bool:
        """Handle shuffle button interaction."""
        try:
            if not self._verify_rotation_disabled():
                return False

            time.sleep(5)
            logger.info("Looking for shuffle button...")

            shuffle_button = self.device.xpath('//*[@resource-id="com.amazon.mp3:id/ShuffleButton"]')
            if not shuffle_button.exists:
                logger.error("Shuffle button not found")
                return False

            shuffle_button.click()
            logger.info("Clicked shuffle button")

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

            if self.needs_restart("Amazon Music"):
                logger.info("Restarting Amazon Music after force-close")
                self.clear_restart_flag("Amazon Music")
                time.sleep(1)

            if not self.start_app():
                return False

            time.sleep(1)
            return self._verify_app_running()

        except Exception as e:
            logger.error(f"Error preparing for action: {e}")
            return False


    def play_pause(self) -> bool:
        """Toggle play/pause with a max 15-second wait for Amazon Music readiness."""
        start_time = time.time()
        try:
            logger.info("Attempting play/pause...")

            # 1. Wait up to 15s for Amazon Music readiness.
            prepared = False
            while time.time() - start_time < 15:
                if self.prepare_for_action():
                    prepared = True
                    break
                time.sleep(2)

            if not prepared:
                logger.warning("Timed out preparing Amazon Music; using keyevent fallback.")
                self.device.shell('input keyevent KEYCODE_MEDIA_PLAY_PAUSE')
                return True

            # 2. If prepared, try the actual UI approach:
            play_button = self.device.xpath('//*[@resource-id="com.amazon.mp3:id/PersistentPlayerPlayButton"]')
            if play_button.exists:
                play_button.click()
                logger.info("Clicked Amazon Music play/pause button")
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
        """Skip to next track with a max 15-second wait for Amazon Music readiness."""
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
                logger.warning("Timed out preparing Amazon Music; using keyevent fallback for next track")
                self.device.shell('input keyevent KEYCODE_MEDIA_NEXT')
                time.sleep(2)
                return True

            # 2. If prepared, try the UI next button.
            next_button = self.device.xpath('//*[@resource-id="com.amazon.mp3:id/PersistentPlayerNextButton"]')
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
        """Go to previous track with a max 15-second wait for Amazon Music readiness."""
        start_time = time.time()
        try:
            logger.info("Amazon Music: Attempting previous track...")

            # Wait up to 15s for Amazon Music to be ready.
            prepared = False
            while time.time() - start_time < 15:
                if self.prepare_for_action():
                    prepared = True
                    break
                time.sleep(2)

            if not prepared:
                logger.warning("Amazon Music: Timed out preparing; using keyevent fallback for previous track")
                self.device.shell('input keyevent KEYCODE_MEDIA_PREVIOUS')
                time.sleep(2)
                return True

            # Try the UI previous button.
            prev_button = self.device.xpath('//*[@resource-id="com.amazon.mp3:id/PersistentPlayerPrevButton"]')
            if prev_button.exists:
                prev_button.click()
                logger.info("Amazon Music: Clicked previous track button")
                time.sleep(2)
                return True

            logger.info("Amazon Music: UI previous button not found; using keyevent fallback")
            self.device.shell('input keyevent KEYCODE_MEDIA_PREVIOUS')
            time.sleep(2)
            return True

        except Exception as e:
            logger.error(f"Amazon Music: Error going to previous track: {e}")
            try:
                self.device.shell('input keyevent KEYCODE_MEDIA_PREVIOUS')
                time.sleep(2)
                return True
            except Exception as ex:
                logger.error(f"Amazon Music: Fallback keyevent failed: {ex}")
                return False

    def like_current_song(self) -> bool:
        """Like current song with a max 15-second wait for Amazon Music readiness."""
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
                logger.warning("Timed out preparing Amazon Music; cannot like song.")
                return False

            # 2. Try to click the 'like' button if it exists.
            like_button = self.device.xpath('//*[@resource-id="com.amazon.mp3:id/StageLikeButtonWrapper"]')
            if not like_button.exists:
                logger.error("Like button not found in Amazon Music.")
                return False

            like_button.click()
            logger.info("Clicked like button in Amazon Music")
            time.sleep(2)
            return True

        except Exception as e:
            logger.error(f"Error liking current song: {e}")
            return False

    def _verify_app_running(self) -> bool:
        """Optimized verification of Amazon Music running state."""
        try:
            if self.device(packageName=self.package_name).exists:
                logger.info("Found Amazon Music UI elements")
                return True

            current_app = self.device.app_current()
            if current_app.get('package') == self.package_name:
                logger.info("Amazon Music is current app")
                return True

            if self.package_name in self.device.shell('dumpsys activity activities | grep -i "mResumedActivity"'):
                logger.info("Amazon Music found in resumed activities")
                return True

            return False
        except Exception as e:
            logger.error(f"Error verifying app state: {e}")
            return False

    def stop_app(self) -> bool:
        """Stop Amazon Music app."""
        try:
            self.device.app_stop(self.package_name)
            time.sleep(1)
            # Verify app is actually stopped
            if self.is_running():
                logger.warning("App still running after stop attempt, trying force-stop")
                return self.force_stop()
            return True
        except Exception as e:
            logger.error(f"Error stopping Amazon Music: {e}")
            return False

    def start_app(self) -> bool:
        """Start Amazon Music app with optimized timing."""
        initial_state = None
        try:
            logger.info("Starting Amazon Music...")
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
                logger.info("Amazon Music started successfully with monkey command")
                return True

            # Fallback to activity manager if monkey fails
            logger.info("Monkey command failed, trying activity manager...")
            self.device.shell(
                f'am start -W -n {self.package_name}/com.amazon.mp3.activity.MainActivity --activity-single-top'
            )
            time.sleep(2)

            # One retry with shorter interval
            if not self._verify_app_running():
                time.sleep(1)
                if self._verify_app_running():
                    logger.info("Amazon Music started successfully after retry")
                    return True
                logger.error("Failed to start Amazon Music")
                return False

            logger.info("Amazon Music started successfully")
            return True

        except Exception as e:
            logger.error(f"Error starting Amazon Music: {e}")
            return False
        finally:
            if initial_state:
                self._restore_rotation_state(initial_state)

    def is_running(self) -> bool:
        """Check if Amazon Music is running with improved detection."""
        try:
            return self._verify_app_running()
        except Exception as e:
            logger.error(f"Error checking if Amazon Music is running: {e}")
            return False

    def force_stop(self) -> bool:
        """Force stop Amazon Music."""
        try:
            self.device.app_stop(self.package_name)
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error force stopping Amazon Music: {e}")
            return False

    def manage_window_state(self, minimize: bool = True) -> bool:
        """Manage Amazon Music window state."""
        try:
            if minimize:
                logger.info("Minimizing Amazon Music window")
                self.device.press("home")
                time.sleep(1)
                return True
            else:
                logger.info("Maximizing Amazon Music window")
                if self.is_running():
                    # Use monkey command for more reliable app switching
                    command = (
                        "monkey -p com.amazon.mp3 -c android.intent.category.LAUNCHER 1"
                    )
                    self.device.shell(command)
                    time.sleep(3)
                    return True
                else:
                    return self.start_app()
        except Exception as e:
            logger.error(f"Failed to manage window state: {e}")
            return False