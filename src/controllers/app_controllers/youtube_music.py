# src/controllers/app_controllers/youtube_music.py

import time
from typing import Optional, Dict
import uiautomator2 as u2
from src.controllers.base_controller import BaseController
from src.controllers.mixins.popup_monitor import PopupMonitorMixin
from src.constants.app_configs import YouTubeMusicConfig, IsoClipboardConfig
from src.utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class YouTubeMusicController(BaseController, PopupMonitorMixin):
    """Controller for YouTube Music automation."""

    def __init__(self, device: u2.Device):
        """Initialize YouTube Music controller."""
        super().__init__(device)
        PopupMonitorMixin.__init__(self)
        self.package_name = YouTubeMusicConfig.PACKAGE_NAME
        self.app_name = YouTubeMusicConfig.APP_NAME
        self.isoclipboard_package = IsoClipboardConfig.PACKAGE_NAME

        # Register apps for monitoring
        self.register_app_for_monitoring("YouTube Music")
        self.register_app_for_monitoring("IsoClipboard")

        # Start popup monitor
        self.start_popup_monitor()

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

    def ensure_screen_active(self) -> bool:
        """Ensure the Android device screen is active."""
        try:
            initial_settings = self.get_rotation_settings()
            logger.info(f"Initial rotation settings before screen activation: {initial_settings}")

            screen_state = self.device.info.get('screenOn')
            if not screen_state:
                self.device.press("power")
                time.sleep(2)
                if not self.device.info.get('screenOn'):
                    logger.error("Failed to activate screen")
                    return False

            current_settings = self.get_rotation_settings()
            if current_settings != initial_settings:
                logger.warning("Rotation settings changed during screen activation!")
                self._restore_rotation_state(initial_settings)

            logger.info("Screen is active")
            return True
        except Exception as e:
            logger.error(f"Error ensuring screen is active: {e}")
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

    def start_initial_automation(self) -> bool:
        """Execute initial automation steps."""
        try:
            # Step 1: Ensure screen is active
            logger.info("Step 1: Ensuring screen is active")
            if not self.ensure_screen_active():
                return False

            # Step 2: Check and close YouTube Music if running
            logger.info("Step 2: Checking and closing YouTube Music if running")
            if self.is_running():
                if not self.stop_app():
                    logger.error("Failed to stop YouTube Music")
                    return False
                time.sleep(2)

            # Step 3: Handle IsoClipboard automation
            logger.info("Step 3: Starting IsoClipboard automation")
            if not self.handle_isoclipboard():
                return False

            logger.info("Successfully completed initial automation steps")
            return True
        except Exception as e:
            logger.error(f"Error in initial automation: {e}")
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

            # Start IsoClipboard with restart handling
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

            # Check for YouTube Music restart
            if self.needs_restart("YouTube Music"):
                logger.info("Restarting YouTube Music after force-close")
                self.clear_restart_flag("YouTube Music")
                time.sleep(2)
                if not self.prepare_for_action():
                    return False

            if not self._handle_menu_interaction():
                return False

            return self._verify_and_cleanup()
        except Exception as e:
            logger.error(f"Error in IsoClipboard handling: {e}")
            return False
        finally:
            if initial_rotation_state:
                self._restore_rotation_state(initial_rotation_state)

    def _start_isoclipboard_safely(self) -> bool:
        """Start IsoClipboard app with safety checks."""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logger.info(f"Starting IsoClipboard attempt {attempt + 1}/{max_attempts}")

                # Close existing instance if running
                self.device.app_stop(self.isoclipboard_package)
                time.sleep(1)

                # Start app using activity manager
                self.device.shell(
                    f'am start -W {self.isoclipboard_package}/.MainActivity --activity-single-top'
                )
                time.sleep(3)

                # Verify rotation is still disabled
                if not self._verify_rotation_disabled():
                    logger.error("Rotation got enabled during app start")
                    continue

                # Multiple verification attempts for foreground status
                for _ in range(3):
                    current_app = self.device.app_current()
                    if current_app.get('package') == self.isoclipboard_package:
                        logger.info("IsoClipboard successfully brought to foreground")
                        return True
                    logger.warning("IsoClipboard not in foreground, retrying...")
                    self.device.press("home")
                    time.sleep(1)
                    self.device.shell(
                        f'am start -W {self.isoclipboard_package}/.MainActivity --activity-single-top'
                    )
                    time.sleep(2)

                logger.error(f"Failed to bring IsoClipboard to foreground on attempt {attempt + 1}")

            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}: {e}")

            time.sleep(2)

        logger.error("All attempts to start IsoClipboard safely failed")
        return False

    def _handle_fetch_operation(self) -> bool:
        """Handle the FETCH button operation safely."""
        try:
            # Verify rotation before fetch
            if not self._verify_rotation_disabled():
                return False

            # Try the exact XPath first
            fetch_xpath = '//*[@resource-id="com.example.isolatedclipboard:id/buttonFetchUrl4"]'
            fetch_button = self.device.xpath(fetch_xpath)

            if fetch_button.exists:
                fetch_button.click()
                logger.info("Clicked FETCH YTM button using XPath")
                time.sleep(5)
            else:
                # Fallback to resourceId if XPath fails
                fetch_button = self.device(resourceId="com.example.isolatedclipboard:id/buttonFetchUrl4")
                if not fetch_button.exists:
                    logger.error("FETCH YTM button not found")
                    return False

                fetch_button.click()
                logger.info("Clicked FETCH YTM button using resourceId")
                time.sleep(5)

            # Verify internet connection
            if not self.check_internet_connection():
                logger.error("No internet connection available")
                return False

            return True
        except Exception as e:
            logger.error(f"Error in fetch operation: {e}")
            return False

    def _handle_menu_interaction(self) -> bool:
        """Handle menu interactions including three dots and shuffle."""
        try:
            if not self._verify_rotation_disabled():
                return False

            # Try multiple XPaths for three dots menu
            three_dots_xpaths = [
                ('//*[@resource-id="com.google.android.apps.youtube.music:id/elements_container"]'
                 '/android.view.ViewGroup[1]/android.view.ViewGroup[6]/android.widget.ImageView[2]'),
                ('//*[@resource-id="com.google.android.apps.youtube.music:id/elements_container"]'
                 '/android.view.ViewGroup[1]/android.view.ViewGroup[6]/android.widget.ImageView[1]'),
                ('//*[@resource-id="com.google.android.apps.youtube.music:id/elements_container"]'
                 '/android.view.ViewGroup[1]/android.view.ViewGroup[5]/android.widget.ImageView[2]'),
                ('//*[@resource-id="com.google.android.apps.youtube.music:id/elements_container"]'
                 '/android.view.ViewGroup[1]/android.view.ViewGroup[5]/android.widget.ImageView[1]')
            ]

            dots_clicked = False
            for xpath in three_dots_xpaths:
                try:
                    element = self.device.xpath(xpath)
                    if element.exists:
                        element.click()
                        logger.info(f"Clicked three dots menu using XPath: {xpath}")
                        dots_clicked = True
                        break
                except Exception as e:
                    logger.debug(f"Failed to click using XPath {xpath}: {e}")
                    continue

            if not dots_clicked:
                logger.warning("All XPath attempts failed, using fallback coordinates")
                self.device.click(835, 1135)
                logger.info("Clicked using fallback coordinates")

            time.sleep(3)

            # Handle shuffle play
            return self._click_shuffle_play()

        except Exception as e:
            logger.error(f"Error in menu interaction: {e}")
            return False

    def _click_shuffle_play(self) -> bool:
        """Click shuffle play button with fallback options."""
        try:
            # Verify rotation is still disabled
            if not self._verify_rotation_disabled():
                return False

            # Try text-based button first
            shuffle_button = self.device(text="Shuffle play", packageName=self.package_name)
            if shuffle_button.exists:
                shuffle_button.click()
                logger.info("Clicked Shuffle play via text")
                time.sleep(2)
                return True

            # Try XPath as fallback
            shuffle_xpath = '//*[@resource-id="com.google.android.apps.youtube.music:id/bottom_sheet_list"]/android.widget.FrameLayout[1]'
            shuffle_element = self.device.xpath(shuffle_xpath)
            if shuffle_element.exists:
                shuffle_element.click()
                logger.info("Clicked shuffle via XPath")
                time.sleep(2)
                return True

            logger.error("Failed to find Shuffle play button")
            return False
        except Exception as e:
            logger.error(f"Error clicking shuffle play: {e}")
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

    def next_track(self) -> bool:
        """Skip to next track with popup monitoring."""
        try:
            logger.info("Attempting next track...")

            if not self.prepare_for_action():
                if self.needs_restart("YouTube Music"):
                    logger.info("Retrying after force-close")
                    self.clear_restart_flag("YouTube Music")
                    time.sleep(2)
                    if not self.prepare_for_action():
                        logger.info("Using keyevent fallback")
                    self.device.shell('input keyevent KEYCODE_MEDIA_NEXT')
                    return True

            max_attempts = 3
            for attempt in range(max_attempts):
                if self.needs_restart("YouTube Music"):
                    logger.info("App was force-closed, retrying...")
                    self.clear_restart_flag("YouTube Music")
                    if not self.prepare_for_action():
                        continue

                next_button = self.device(
                    resourceId=f"{self.package_name}:id/player_control_next_button"
                )
                if next_button.exists:
                    next_button.click()
                    logger.info("Clicked next track button")
                    time.sleep(2)
                    return True

                logger.warning(f"Next button not found, attempt {attempt + 1}/{max_attempts}")
                time.sleep(2)

            # Fallback to keyevent
            logger.info("UI attempts failed, using keyevent")
            self.device.shell('input keyevent KEYCODE_MEDIA_NEXT')
            time.sleep(2)
            return True

        except Exception as e:
            logger.error(f"Error skipping to next track: {e}")
            try:
                self.device.shell('input keyevent KEYCODE_MEDIA_NEXT')
                logger.info("Sent next track keyevent after error")
                time.sleep(2)
                return True
            except:
                return False

    def previous_track(self) -> bool:
        """Go to previous track with popup monitoring."""
        try:
            logger.info("Attempting previous track...")

            if not self.prepare_for_action():
                if self.needs_restart("YouTube Music"):
                    logger.info("Retrying after force-close")
                    self.clear_restart_flag("YouTube Music")
                    time.sleep(2)
                    if not self.prepare_for_action():
                        logger.info("Using keyevent fallback")
                        self.device.shell('input keyevent KEYCODE_MEDIA_PREVIOUS')
                        return True
                else:
                    logger.info("Using keyevent fallback")
                    self.device.shell('input keyevent KEYCODE_MEDIA_PREVIOUS')
                    return True

            max_attempts = 3
            for attempt in range(max_attempts):
                if self.needs_restart("YouTube Music"):
                    logger.info("App was force-closed, retrying...")
                    self.clear_restart_flag("YouTube Music")
                    if not self.prepare_for_action():
                        continue

                prev_button = self.device(
                    resourceId=f"{self.package_name}:id/player_control_previous_button"
                )
                if prev_button.exists:
                    prev_button.click()
                    logger.info("Clicked previous track button")
                    time.sleep(2)
                    return True

                logger.warning(f"Previous button not found, attempt {attempt + 1}/{max_attempts}")
                time.sleep(2)

            # Fallback to keyevent
            logger.info("UI attempts failed, using keyevent")
            self.device.shell('input keyevent KEYCODE_MEDIA_PREVIOUS')
            time.sleep(2)
            return True

        except Exception as e:
            logger.error(f"Error going to previous track: {e}")
            try:
                self.device.shell('input keyevent KEYCODE_MEDIA_PREVIOUS')
                logger.info("Sent previous track keyevent after error")
                time.sleep(2)
                return True
            except:
                return False

    def play_pause(self) -> bool:
        """Toggle play/pause state with keyevent fallback."""
        try:
            logger.info("Attempting play/pause...")

            if not self.prepare_for_action():
                if self.needs_restart("YouTube Music"):
                    logger.info("Retrying after force-close")
                    self.clear_restart_flag("YouTube Music")
                    time.sleep(2)
                    if not self.prepare_for_action():
                        logger.info("Using keyevent fallback")
                        self.device.shell('input keyevent KEYCODE_MEDIA_PLAY_PAUSE')
                        return True
                else:
                    logger.info("Using keyevent fallback")
                    self.device.shell('input keyevent KEYCODE_MEDIA_PLAY_PAUSE')
                    return True

            play_button = self.device(
                resourceId=f"{self.package_name}:id/player_control_play_pause_replay_button"
            )
            if play_button.exists:
                play_button.click()
                logger.info("Clicked play/pause button via UI")
                time.sleep(1)
                return True

            # Fallback to keyevent
            logger.info("Play button not found, using keyevent")
            self.device.shell('input keyevent KEYCODE_MEDIA_PLAY_PAUSE')
            time.sleep(1)
            return True

        except Exception as e:
            logger.error(f"Error toggling play/pause: {e}")
            try:
                self.device.shell('input keyevent KEYCODE_MEDIA_PLAY_PAUSE')
                logger.info("Sent play/pause keyevent after error")
                time.sleep(1)
                return True
            except:
                return False

    def like_current_song(self) -> bool:
        """Like current song with popup monitoring."""
        try:
            logger.info("Starting like song action...")

            if not self.prepare_for_action():
                if self.needs_restart("YouTube Music"):
                    logger.info("Retrying after force-close")
                    self.clear_restart_flag("YouTube Music")
                    time.sleep(2)
                    if not self.prepare_for_action():
                        return False
                else:
                    return False

            # Try XPath first
            xpath = ('//*[contains(@content-desc, "like this video along with") '
                     'and contains(@content-desc, "other people")]/android.view.ViewGroup[1]')
            like_button = self.device.xpath(xpath)

            if like_button.exists:
                logger.info("Found like button via XPath")
                like_button.click()
                time.sleep(2)
                return True

            # Try fallback coordinates if needed
            screen_w, screen_h = self.device.window_size()
            x = int(0.113 * screen_w)
            y = int(0.623 * screen_h)

            logger.info(f"Using fallback coordinates: x={x}, y={y}")
            self.device.click(x, y)
            time.sleep(2)
            return True

        except Exception as e:
            logger.error(f"Error liking song: {e}")
            return False

    def start_app(self) -> bool:
        """Start YouTube Music app."""
        try:
            logger.info("Starting YouTube Music...")
            initial_state = self.get_rotation_settings()

            # Force disable rotation first
            if not self._force_disable_rotation():
                return False

            # Start app using activity manager for more reliable launch
            self.device.shell(
                f'am start -W {self.package_name}/com.google.android.apps.youtube.music.activities.MusicActivity --activity-single-top'
            )
            time.sleep(3)

            # Verify app is running
            if not self.is_running():
                logger.error("Failed to verify YouTube Music is running")
                return False

            # Verify app is in foreground
            current_app = self.device.app_current()
            if current_app.get('package') != self.package_name:
                logger.error("YouTube Music is not in foreground")
                # Try to bring to foreground
                self.device.app_start(self.package_name)
                time.sleep(2)

                # Check again
                current_app = self.device.app_current()
                if current_app.get('package') != self.package_name:
                    return False

            logger.info("YouTube Music started successfully")
            return True

        except Exception as e:
            logger.error(f"Error starting YouTube Music: {e}")
            return False
        finally:
            # Restore original rotation state
            self._restore_rotation_state(initial_state)

    def stop_app(self) -> bool:
        """Stop YouTube Music app."""
        try:
            self.device.app_stop(self.package_name)
            time.sleep(1)
            # Verify app is actually stopped
            if self.is_running():
                logger.warning("App still running after stop attempt, trying force-stop")
                return self.force_stop()
            return True
        except Exception as e:
            logger.error(f"Error stopping YouTube Music: {e}")
            return False

    def is_running(self) -> bool:
        """Check if YouTube Music is running."""
        try:
            return bool(self.device(packageName=self.package_name).exists)
        except Exception as e:
            logger.error(f"Error checking if YouTube Music is running: {e}")
            return False

    def manage_window_state(self, minimize: bool = True) -> bool:
        """Manage YouTube Music window state."""
        try:
            if minimize:
                self.device.press("home")
                logger.info("Minimized YouTube Music window")
            else:
                self.device.app_start(self.package_name)
                logger.info("Maximized YouTube Music window")
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Failed to manage window state: {e}")
            return False

    def force_stop(self) -> bool:
        """Force stop YouTube Music."""
        try:
            self.device.app_stop(self.package_name)
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error force stopping YouTube Music: {e}")
            return False

    def prepare_for_action(self) -> bool:
        """Prepare YouTube Music with improved foreground verification and retry logic."""
        try:
            logger.info("Preparing YouTube Music for action...")
            initial_state = self.get_rotation_settings()

            # Force disable rotation
            if not self._force_disable_rotation():
                return False

            max_attempts = 3
            for attempt in range(max_attempts):
                logger.info("Going to home screen for clean state...")
                self.device.shell('input keyevent KEYCODE_HOME')
                time.sleep(1)

                logger.info("Starting YouTube Music activity...")
                self.device.shell(
                    f'am start -W {self.package_name}/com.google.android.apps.youtube.music.activities.MusicActivity --activity-single-top'
                )
                time.sleep(3)

                # Verify app is running
                if not self.is_running():
                    logger.error(f"Failed to start YouTube Music (attempt {attempt + 1})")
                    continue

                # Verify app is in foreground
                current_app = self.device.app_current()
                if current_app.get('package') != self.package_name:
                    logger.error(f"YouTube Music not in foreground (attempt {attempt + 1})")

                    # Recovery steps
                    logger.info("Attempting recovery steps...")

                    # Step 1: Go home and retry direct launch
                    self.device.shell('input keyevent KEYCODE_HOME')
                    time.sleep(1)
                    self.device.app_start(self.package_name)
                    time.sleep(2)

                    # Check if recovery worked
                    current_app = self.device.app_current()
                    if current_app.get('package') == self.package_name:
                        logger.info("Recovery successful using direct launch")
                        return True

                    # Step 2: Try force-stop and restart
                    logger.info("Trying force-stop and restart...")
                    self.force_stop()
                    time.sleep(2)
                    self.device.shell('input keyevent KEYCODE_HOME')
                    time.sleep(1)
                    self.device.shell(
                        f'am start -W {self.package_name}/com.google.android.apps.youtube.music.activities.MusicActivity --activity-single-top'
                    )
                    time.sleep(3)

                    current_app = self.device.app_current()
                    if current_app.get('package') == self.package_name:
                        logger.info("Recovery successful using force-stop and restart")
                        return True

                    continue

                logger.info("YouTube Music successfully prepared for action")
                return True

            logger.error("Failed to prepare YouTube Music after all attempts")
            return False

        except Exception as e:
            logger.error(f"Error preparing YouTube Music: {e}")
            return False
        finally:
            # Restore original rotation state
            self._restore_rotation_state(initial_state)

    def _verify_and_cleanup(self) -> bool:
        """Final verification and cleanup steps."""
        try:
            # Ensure rotation is still disabled
            if not self._verify_rotation_disabled():
                return False

            # Return to home screen
            self.device.press("home")
            time.sleep(1)

            return True
        except Exception as e:
            logger.error(f"Error in verification and cleanup: {e}")
            return False
            self.device.shell('input keyevent KEYCODE_MEDIA_NEXT')
            return True
        else:
            logger.info("Using keyevent fallback")