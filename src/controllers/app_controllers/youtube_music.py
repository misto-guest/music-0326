# src/controllers/app_controllers/youtube_music.py

import time
from typing import Optional
import uiautomator2 as u2
from src.controllers.base_controller import BaseController
from src.constants.app_configs import YouTubeMusicConfig, IsoClipboardConfig
from src.utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class YouTubeMusicController(BaseController):
    """Controller for YouTube Music automation."""

    def __init__(self, device: u2.Device):
        """Initialize YouTube Music controller."""
        super().__init__(device)
        self.package_name = YouTubeMusicConfig.PACKAGE_NAME
        self.app_name = YouTubeMusicConfig.APP_NAME
        self.isoclipboard_package = IsoClipboardConfig.PACKAGE_NAME

    def get_rotation_settings(self) -> dict:
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

    def handle_rotation_state(self) -> bool:
        """Handle rotation state, including force-stopping if app was launched with auto-rotate."""
        try:
            # Get initial rotation settings
            settings = self.get_rotation_settings()
            if not settings:
                logger.error("Failed to get rotation settings")
                return False

            # If auto-rotate is enabled and app is running, force stop
            if settings['auto_rotate'] == '1' and self.is_running():
                logger.info("App was launched with auto-rotate enabled, forcing stop")
                self.force_stop()
                time.sleep(2)

            # Disable auto-rotate and force portrait
            self.device.shell('settings put system accelerometer_rotation 0')
            time.sleep(1)
            self.device.shell('settings put system user_rotation 0')
            time.sleep(1)

            # Verify settings were applied
            new_settings = self.get_rotation_settings()
            if not new_settings:
                logger.error("Failed to verify new rotation settings")
                return False

            if new_settings['auto_rotate'] != '0' or new_settings['user_rotation'] != '0':
                logger.error(f"Failed to apply rotation settings. Current state: {new_settings}")
                return False

            logger.info("Rotation settings successfully applied")
            return True

        except Exception as e:
            logger.error(f"Error handling rotation state: {e}")
            return False

    def verify_rotation_settings(self) -> bool:
        """Verify current rotation settings are correct."""
        try:
            settings = self.get_rotation_settings()
            if not settings:
                return False

            is_correct = (settings['auto_rotate'] == '0' and settings['user_rotation'] == '0')
            if not is_correct:
                logger.warning(f"Incorrect rotation settings detected: {settings}")

            return is_correct

        except Exception as e:
            logger.error(f"Error verifying rotation settings: {e}")
            return False

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
                self.device.shell(f'settings put system accelerometer_rotation {initial_settings["auto_rotate"]}')
                self.device.shell(f'settings put system user_rotation {initial_settings["user_rotation"]}')

            logger.info("Screen is active")
            return True
        except Exception as e:
            logger.error(f"Error ensuring screen is active: {e}")
            return False

    def manage_window_state(self, minimize: bool = True) -> bool:
        try:
            if minimize:
                self.device.press("home")
                logger.info("Minimized YouTube Music window")
            else:
                self.device.app_start(self.package_name)
                logger.info("Maximized YouTube Music window")
            return True
        except Exception as e:
            logger.error(f"Failed to manage window state: {e}")
            return False

    def close_youtube_music(self) -> bool:
        """Close YouTube Music app if it's running."""
        try:
            if self.is_running():
                logger.info("YouTube Music is running, closing it")
                if not self.force_stop():
                    logger.error("Failed to force stop YouTube Music")
                    return False
                time.sleep(2)  # Wait for app to fully close

                # Verify app is closed
                if self.is_running():
                    logger.error("YouTube Music is still running after force stop")
                    return False

            logger.info("YouTube Music is not running")
            return True

        except Exception as e:
            logger.error(f"Error closing YouTube Music: {e}")
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
            if not self.close_youtube_music():
                return False

            # Step 3: Handle IsoClipboard automation
            logger.info("Step 3: Starting IsoClipboard automation")
            if not self.handle_isoclipboard():
                return False

            logger.info("Successfully completed initial automation steps")
            return True

        except Exception as e:
            logger.error(f"Error in initial automation: {e}")
            return False

    def check_internet_connection(self, max_retries: int = 5, delay: int = 2) -> bool:
        """Check internet connection using netstat to verify active TCP connections.

        Args:
            max_retries: Maximum number of retry attempts
            delay: Delay in seconds between retries

        Returns:
            bool: True if internet connection is available, False otherwise
        """
        for attempt in range(max_retries):
            try:
                # Get all TCP connections (both IPv4 and IPv6-mapped IPv4)
                netstat_check = self.device.shell('netstat -n | grep ESTABLISHED | grep -E "^tcp6.*::ffff:|^tcp[^6]"')

                # First check exit code
                if getattr(netstat_check, 'exit_code', 0) != 0:
                    logger.warning(
                        f"Failed to get TCP connections (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {delay}s...")
                    time.sleep(delay)
                    continue

                # Get actual output content
                output = str(getattr(netstat_check, 'output', netstat_check)).strip()
                if not output:  # Check if output is empty
                    logger.warning(
                        f"No TCP connections found (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {delay}s...")
                    time.sleep(delay)
                    continue

                connections = output.split('\n')
                logger.info(f"Found {len(connections)} TCP connections")
                logger.info(f"Sample connection: {connections[0] if connections else 'None'}")
                return True

            except Exception as e:
                logger.error(f"Error checking internet connection: {e}")
                time.sleep(delay)

        logger.error("Failed to establish internet connection after retries.")
        return False

    def handle_isoclipboard(self) -> bool:
        """Handle IsoClipboard while maintaining rotation settings."""
        try:
            # Force disable auto-rotate before starting
            self.device.shell('settings put system accelerometer_rotation 0')
            time.sleep(1)  # Wait for setting to apply

            # Start the IsoClipboard app
            self.device.app_start(self.isoclipboard_package)
            time.sleep(2)

            # Force disable auto-rotate again after app starts
            self.device.shell('settings put system accelerometer_rotation 0')
            time.sleep(1)

            # Click the FETCH button
            fetch_button = self.device(resourceId=f"{self.isoclipboard_package}:id/buttonFetchUrl4")
            if not fetch_button.exists:
                logger.error("FETCH button not found")
                return False
            fetch_button.click()
            logger.info("Clicked FETCH")

            # Verify internet connection
            if not self.check_internet_connection():
                logger.error("No internet connection available")
                return False
            time.sleep(3)

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

            # Force disable auto-rotate before menu interaction
            self.device.shell('settings put system accelerometer_rotation 0')
            time.sleep(1)

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

            # Force disable auto-rotate before shuffle
            self.device.shell('settings put system accelerometer_rotation 0')
            time.sleep(1)

            # Attempt to click the Shuffle play button
            shuffle_button = self.device(text="Shuffle play", packageName=self.package_name)
            if shuffle_button.exists:
                shuffle_button.click()
                logger.info("Clicked Shuffle play")
                time.sleep(5)
                self.device.press("home")
                return True

            shuffle_xpath = '//*[@resource-id="com.google.android.apps.youtube.music:id/bottom_sheet_list"]/android.widget.FrameLayout[1]'
            shuffle_element = self.device.xpath(shuffle_xpath)
            if shuffle_element.exists:
                shuffle_element.click()
                logger.info("Clicked shuffle button via XPath")
                time.sleep(5)
                self.device.press("home")
                return True

            logger.error("Failed to find Shuffle play button")
            return False

        except Exception as e:
            logger.error(f"Error with IsoClipboard: {e}")
            return False
        finally:
            # Always ensure auto-rotate is disabled at the end
            try:
                self.device.shell('settings put system accelerometer_rotation 0')
            except Exception as e:
                logger.error(f"Error disabling auto-rotate in finally block: {e}")

    def play_pause(self) -> bool:
        """Toggle play/pause state."""
        try:
            play_button = self.device(
                resourceId="com.google.android.apps.youtube.music:id/player_control_play_pause_replay_button"
            )
            if not play_button.exists:
                logger.error("Play/pause button not found")
                return False

            play_button.click()
            logger.info("Clicked play/pause button")
            return True

        except Exception as e:
            logger.error(f"Error toggling play/pause: {e}")
            return False

    def next_track(self) -> bool:
        """Skip to next track with improved reliability."""
        try:
            logger.info("Attempting to click next track button...")

            # First ensure we're properly prepared
            if not self.prepare_for_action():
                logger.error("Failed to prepare for next track action")
                return False

            # Try to find the next button with multiple attempts
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

                # Try to bring app to foreground again
                self.device.app_start(self.package_name)
                time.sleep(2)

            logger.error("Next track button not found after all attempts")
            return False

        except Exception as e:
            logger.error(f"Error skipping to next track: {e}")
            return False

    def previous_track(self) -> bool:
        """Go to previous track with proper app preparation."""
        try:
            logger.info("Attempting to click previous track button...")

            # First ensure we're properly prepared
            if not self.prepare_for_action():
                logger.error("Failed to prepare for previous track action")
                return False

            # Try to find the previous button with multiple attempts
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

                # Try to bring app to foreground again
                self.device.app_start(self.package_name)
                time.sleep(2)

            logger.error("Previous track button not found after all attempts")
            return False

        except Exception as e:
            logger.error(f"Error going to previous track: {e}")
            return False

    def like_current_song(self) -> bool:
        """Like current song with proper app preparation and state verification."""
        try:
            logger.info("Starting like song action...")

            # First ensure we're properly prepared
            if not self.prepare_for_action():
                logger.error("Failed to prepare for like action")
                return False

            # Verify app is actually running
            is_running = self.is_running()
            logger.info(f"Is YouTube Music running? {is_running}")
            if not is_running:
                logger.error("YouTube Music is not running after preparation")
                return False

            # Get current app info
            current_app = self.device.app_current()
            logger.info(f"Current app package: {current_app.get('package')}")
            if current_app.get('package') != self.package_name:
                logger.error("YouTube Music is not in foreground")
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
            # Get screen dimensions
            screen_w, screen_h = self.device.window_size()
            logger.info(f"Screen dimensions: {screen_w}x{screen_h}")

            # Calculate and log coordinates before clicking
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

    def start_app(self) -> bool:
        """Start YouTube Music with proper rotation handling."""
        try:
            # First handle rotation state
            if not self.handle_rotation_state():
                logger.error("Failed to handle rotation state")
                return False

            # Start the app
            self.device.app_start(self.package_name)
            time.sleep(3)

            # Verify app is running
            if not self.is_running():
                logger.error("App failed to start")
                return False

            # Verify rotation settings maintained
            if not self.verify_rotation_settings():
                logger.warning("Rotation settings changed after app start, attempting to fix")
                return self.handle_rotation_state()

            return True

        except Exception as e:
            logger.error(f"Error starting YouTube Music: {e}")
            return False

    def stop_app(self) -> bool:
        try:
            self.device.app_stop(self.package_name)
            return True
        except Exception as e:
            logger.error(f"Error stopping YouTube Music: {e}")
            return False

    def is_running(self) -> bool:
        try:
            return bool(self.device(packageName=self.package_name).exists)
        except Exception as e:
            logger.error(f"Error checking if YouTube Music is running: {e}")
            return False

    def force_stop(self) -> bool:
        try:
            self.device.app_stop(self.package_name)
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error force stopping YouTube Music: {e}")
            return False

    def ensure_orientation(self) -> bool:
        """Force the screen into portrait mode."""
        try:
            logger.info("Forcing portrait orientation...")
            # Kill any rotation setting daemon
            self.device.shell('pkill rotationcontrol')
            time.sleep(1)

            # Disable auto rotation and force portrait
            cmds = [
                'settings put system accelerometer_rotation 0',
                'settings put system user_rotation 0',
            ]

            for cmd in cmds:
                self.device.shell(cmd)
                time.sleep(0.5)

            return True
        except Exception as e:
            logger.error(f"Error forcing orientation: {e}")
            return False

    def prepare_for_action(self) -> bool:
        try:
            logger.info("Preparing YouTube Music for action...")

            if not self.verify_rotation_settings():
                if not self.handle_rotation_state():
                    logger.error("Failed to handle rotation state")
                    return False

            # Force stop if app was previously running
            if self.is_running():
                self.force_stop()
                time.sleep(2)

            # Start app using activity manager
            self.device.shell(
                f'am start -W {self.package_name}/com.google.android.apps.youtube.music.activities.MusicActivity --activity-single-top')
            time.sleep(3)

            # Verify app is in foreground
            current_app = self.device.app_current()
            if current_app.get('package') != self.package_name:
                logger.error("YouTube Music is not in foreground")
                return False

            # Check if music is playing
            play_button = self.device(
                resourceId="com.google.android.apps.youtube.music:id/player_control_play_pause_replay_button"
            )

            if not play_button.exists:
                logger.info("No playback detected, starting music...")
                if not self.handle_isoclipboard():
                    logger.error("Failed to start playback")
                    return False
                time.sleep(5)

            # Final rotation verification
            if not self.verify_rotation_settings():
                logger.warning("Rotation settings changed, attempting to fix")
                return self.handle_rotation_state()

            time.sleep(2)
            return True

        except Exception as e:
            logger.error(f"Error preparing YouTube Music: {e}")
            return False

    def bring_to_foreground(self) -> bool:
        """Bring YouTube Music to foreground."""
        try:
            logger.info("Bringing YouTube Music to foreground...")
            self.device.app_start(self.package_name)
            time.sleep(2)  # Wait for app to come to foreground

            # Verify app is in foreground
            if self.device(packageName=self.package_name).exists:
                logger.info("YouTube Music brought to foreground successfully")
                return True

            logger.error("Failed to verify YouTube Music in foreground")
            return False

        except Exception as e:
            logger.error(f"Error bringing YouTube Music to foreground: {e}")
            return False