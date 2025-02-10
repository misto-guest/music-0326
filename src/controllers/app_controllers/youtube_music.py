# src/controllers/app_controllers/youtube_music.py

import time
from typing import Optional, Dict
import uiautomator2 as u2
from src.controllers.base_controller import BaseController
from src.constants.app_configs import YouTubeMusicConfig, IsoClipboardConfig
from src.utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class YouTubeMusicController(BaseController):
    """Controller for YouTube Music automation with improved rotation handling."""

    def __init__(self, device: u2.Device):
        """Initialize YouTube Music controller."""
        super().__init__(device)
        self.package_name = YouTubeMusicConfig.PACKAGE_NAME
        self.app_name = YouTubeMusicConfig.APP_NAME
        self.isoclipboard_package = IsoClipboardConfig.PACKAGE_NAME

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
        """Ensure the Android device screen is active while monitoring rotation settings."""
        try:
            # Check initial rotation settings
            initial_settings = self.get_rotation_settings()
            logger.info(f"Initial rotation settings before screen activation: {initial_settings}")

            # Original screen activation code
            screen_state = self.device.info.get('screenOn')
            if not screen_state:
                self.device.press("power")
                time.sleep(2)
                if not self.device.info.get('screenOn'):
                    logger.error("Failed to activate screen")
                    return False

            # Check if rotation settings changed
            current_settings = self.get_rotation_settings()
            if current_settings != initial_settings:
                logger.warning(f"Rotation settings changed during screen activation!")
                logger.warning(f"Before: {initial_settings}")
                logger.warning(f"After: {current_settings}")
                # Restore original settings
                self._restore_rotation_state(initial_settings)

            logger.info("Screen is active")
            return True
        except Exception as e:
            logger.error(f"Error ensuring screen is active: {e}")
            return False

    def _force_disable_rotation(self) -> bool:
        """Force disable rotation with verification."""
        try:
            # Disable rotation multiple times with verification
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

    def handle_isoclipboard(self) -> bool:
        """Handle IsoClipboard with strict rotation control and state verification."""
        initial_rotation_state = None
        try:
            # 1. Save initial rotation state
            initial_rotation_state = self.get_rotation_settings()
            logger.info(f"Initial rotation settings: {initial_rotation_state}")

            # 2. Force disable rotation with verification
            if not self._force_disable_rotation():
                logger.error("Failed to disable rotation")
                return False

            # 3. Start IsoClipboard with state verification
            if not self._start_isoclipboard_safely():
                return False

            # 4. Handle the FETCH operation
            if not self._handle_fetch_operation():
                return False

            # 5. Handle menu interaction
            if not self._handle_menu_interaction():
                return False

            # 6. Final verification and cleanup
            return self._verify_and_cleanup()

        except Exception as e:
            logger.error(f"Error in IsoClipboard handling: {e}")
            return False
        finally:
            # Always restore initial rotation state
            if initial_rotation_state:
                self._restore_rotation_state(initial_rotation_state)

    def _start_isoclipboard_safely(self) -> bool:
        """Start IsoClipboard app with safety checks and retries."""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logger.info(f"Starting IsoClipboard attempt {attempt + 1}/{max_attempts}")

                # Close existing instance if running
                self.device.app_stop(self.isoclipboard_package)
                time.sleep(1)

                # Start app using activity manager for more reliable launch
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

            # Wait before next attempt
            time.sleep(2)

        logger.error("All attempts to start IsoClipboard safely failed")
        return False

    def _handle_fetch_operation(self) -> bool:
        """Handle the FETCH button operation safely."""
        try:
            # Verify rotation before fetch
            if not self._verify_rotation_disabled():
                return False

            # Find and click FETCH button
            fetch_button = self.device(resourceId=f"{self.isoclipboard_package}:id/buttonFetchUrl4")
            if not fetch_button.exists:
                logger.error("FETCH button not found")
                return False

            fetch_button.click()
            logger.info("Clicked FETCH")
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
            if not self._click_shuffle_play():
                return False

            return True
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

    def start_app(self) -> bool:
        """Start YouTube Music with rotation control."""
        try:
            initial_state = self.get_rotation_settings()

            # Force disable rotation first
            if not self._force_disable_rotation():
                return False

            # Start app using activity manager
            self.device.shell(
                f'am start -W {self.package_name}/com.google.android.apps.youtube.music.activities.MusicActivity --activity-single-top')
            time.sleep(3)

            # Verify app is running
            if not self.is_running():
                logger.error("Failed to start YouTube Music")
                return False

            return True
        except Exception as e:
            logger.error(f"Error starting YouTube Music: {e}")
            return False
        finally:
            # Restore original rotation state
            self._restore_rotation_state(initial_state)

    def prepare_for_action(self) -> bool:
        """Prepare YouTube Music with rotation control."""
        try:
            logger.info("Preparing YouTube Music for action...")
            initial_state = self.get_rotation_settings()

            # Force disable rotation
            if not self._force_disable_rotation():
                return False

            # Start app if needed
            if not self.is_running():
                if not self.start_app():
                    return False

            # Verify app is in foreground
            current_app = self.device.app_current()
            if current_app.get('package') != self.package_name:
                logger.error("YouTube Music is not in foreground")
                return False

            return True
        except Exception as e:
            logger.error(f"Error preparing YouTube Music: {e}")
            return False
        finally:
            # Restore original rotation state
            self._restore_rotation_state(initial_state)

    def play_pause(self) -> bool:
        """Toggle play/pause state with keyevent fallback."""
        try:
            if not self.prepare_for_action():
                logger.info("Using keyevent fallback for play/pause")
                self.device.shell('input keyevent KEYCODE_MEDIA_PLAY_PAUSE')
                return True

            play_button = self.device(
                resourceId="com.google.android.apps.youtube.music:id/player_control_play_pause_replay_button"
            )
            if play_button.exists:
                play_button.click()
                logger.info("Clicked play/pause button via UI")
                return True

            # Fallback to keyevent
            logger.info("Play button not found, using keyevent")
            self.device.shell('input keyevent KEYCODE_MEDIA_PLAY_PAUSE')
            return True
        except Exception as e:
            logger.error(f"Error toggling play/pause: {e}")
            return False

    def next_track(self) -> bool:
        """Skip to next track with rotation control."""
        try:
            logger.info("Attempting next track...")
            if not self.prepare_for_action():
                logger.info("Using keyevent fallback for next track")
                self.device.shell('input keyevent KEYCODE_MEDIA_NEXT')
                logger.info("Sent next track keyevent")
                time.sleep(2)
                return True

            # Try UI-based approach with multiple attempts
            max_attempts = 3
            for attempt in range(max_attempts):
                next_button = self.device(
                    resourceId="com.google.android.apps.youtube.music:id/player_control_next_button"
                )
                if next_button.exists:
                    next_button.click()
                    logger.info("Clicked next track button")
                    time.sleep(2)
                    return True

                logger.warning(f"Next button not found, attempt {attempt + 1}/{max_attempts}")
                time.sleep(2)
                self.device.app_start(self.package_name)
                time.sleep(2)

            # Fallback to keyevent
            logger.info("UI attempts failed, using keyevent")
            self.device.shell('input keyevent KEYCODE_MEDIA_NEXT')
            logger.info("Sent next track keyevent")
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
        """Go to previous track with rotation control."""
        try:
            logger.info("Attempting previous track...")
            if not self.prepare_for_action():
                logger.info("Using keyevent fallback for previous track")
                self.device.shell('input keyevent KEYCODE_MEDIA_PREVIOUS')
                logger.info("Sent previous track keyevent")
                time.sleep(2)
                return True

            # Try UI-based approach with multiple attempts
            max_attempts = 3
            for attempt in range(max_attempts):
                prev_button = self.device(
                    resourceId="com.google.android.apps.youtube.music:id/player_control_previous_button"
                )
                if prev_button.exists:
                    prev_button.click()
                    logger.info("Clicked previous track button")
                    time.sleep(2)
                    return True

                logger.warning(f"Previous button not found, attempt {attempt + 1}/{max_attempts}")
                time.sleep(2)
                self.device.app_start(self.package_name)
                time.sleep(2)

            # Fallback to keyevent
            logger.info("UI attempts failed, using keyevent")
            self.device.shell('input keyevent KEYCODE_MEDIA_PREVIOUS')
            logger.info("Sent previous track keyevent")
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

    def like_current_song(self) -> bool:
        """Like current song with improved rotation control."""
        try:
            logger.info("Starting like song action...")
            initial_state = self.get_rotation_settings()

            # First ensure we're properly prepared
            if not self.prepare_for_action():
                logger.error("Failed to prepare for like action")
                return False

            # Verify app is actually running and in foreground
            if not self.is_running():
                logger.error("YouTube Music is not running after preparation")
                return False

            current_app = self.device.app_current()
            if current_app.get('package') != self.package_name:
                logger.error("YouTube Music is not in foreground")
                return False

            # Force disable rotation before interaction
            if not self._force_disable_rotation():
                return False

            # Try XPath first
            logger.info("Attempting to find like button via XPath...")
            xpath = ('//*[contains(@content-desc, "like this video along with") '
                     'and contains(@content-desc, "other people")]/android.view.ViewGroup[1]')
            like_button = self.device.xpath(xpath)
            if like_button.exists:
                logger.info("Found like button via XPath")
                like_button.click()
                time.sleep(2)
                return True

            logger.info("XPath like button not found, trying fallback coordinates...")
            # Get screen dimensions and calculate coordinates
            screen_w, screen_h = self.device.window_size()
            logger.info(f"Screen dimensions: {screen_w}x{screen_h}")

            x = int(0.113 * screen_w)
            y = int(0.623 * screen_h)
            logger.info(f"Using fallback coordinates: x={x}, y={y}")

            self.device.click(x, y)
            time.sleep(2)
            logger.info("Clicked fallback coordinates")
            return True

        except Exception as e:
            logger.error(f"Error liking song: {e}")
            return False
        finally:
            # Restore original rotation state
            self._restore_rotation_state(initial_state)

    def is_running(self) -> bool:
        """Check if YouTube Music is running."""
        try:
            return bool(self.device(packageName=self.package_name).exists)
        except Exception as e:
            logger.error(f"Error checking if YouTube Music is running: {e}")
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

    def bring_to_foreground(self) -> bool:
        """Bring YouTube Music to foreground with rotation control."""
        try:
            logger.info("Bringing YouTube Music to foreground...")
            initial_state = self.get_rotation_settings()

            # Force disable rotation
            if not self._force_disable_rotation():
                return False

            self.device.app_start(self.package_name)
            time.sleep(2)

            # Verify app is in foreground
            if self.device(packageName=self.package_name).exists:
                logger.info("YouTube Music brought to foreground successfully")
                return True

            logger.error("Failed to verify YouTube Music in foreground")
            return False
        except Exception as e:
            logger.error(f"Error bringing YouTube Music to foreground: {e}")
            return False
        finally:
            # Restore original rotation state
            self._restore_rotation_state(initial_state)