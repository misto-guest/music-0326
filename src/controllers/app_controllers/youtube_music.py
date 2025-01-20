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

    def ensure_screen_active(self) -> bool:
        """Ensure the Android device screen is active."""
        try:
            # Check if screen is on
            screen_state = self.device.info.get('screenOn')

            if not screen_state:
                # Press power button to wake the screen
                self.device.press("power")
                time.sleep(2)  # Wait for screen to wake up

                # Verify screen is now on
                if not self.device.info.get('screenOn'):
                    logger.error("Failed to activate screen")
                    return False

            logger.info("Screen is active")
            return True

        except Exception as e:
            logger.error(f"Error ensuring screen is active: {e}")
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
        for attempt in range(max_retries):
            try:
                ping_response = self.device.shell('ping -c 1 -W 1 8.8.8.8')
                ping_output = str(ping_response).strip()

                logger.info(f"Ping result: {ping_output}")

                if 'bytes from 8.8.8.8' in ping_output or '1 packets transmitted, 1 received' in ping_output:
                    logger.info("Internet connection available via ping.")
                    return True

                logger.warning(
                    f"No internet connection detected (attempt {attempt + 1}/{max_retries}). Retrying in {delay}s...")
                time.sleep(delay)

            except Exception as e:
                logger.error(f"Error checking internet connection: {e}")
                time.sleep(delay)

        logger.error("Failed to establish internet connection after retries.")
        return False

    def handle_isoclipboard(self) -> bool:
        """Handle IsoClipboard interaction."""
        try:
            # Start IsoClipboard app
            self.device.app_start(self.isoclipboard_package)
            time.sleep(2)
            fetch_button = self.device(resourceId=f"{self.isoclipboard_package}:id/buttonFetchUrl4")
            if not fetch_button.exists:
                logger.error("FETCH button not found")
                return False
            fetch_button.click()
            logger.info("Clicked FETCH")
            if not self.check_internet_connection():
                logger.error("No internet connection available")
                self.device.shell('am broadcast -a android.intent.action.CLOSE_SYSTEM_DIALOGS')
                self.device.shell('am start -n com.android.settings/.Settings')
                return False

            time.sleep(3)

            try:
                self.device.xpath(
                    '//*[@resource-id="com.google.android.apps.youtube.music:id/elements_container"]'
                    '/android.view.ViewGroup[1]/android.view.ViewGroup[6]/android.widget.ImageView[1]').click()
                logger.info("Clicked using direct XPath")
            except:
                logger.warning("XPath 3dots failed, trying coordinates")
                self.device.click(835, 1135)
                logger.info("Clicked using coordinates")

            time.sleep(3)
            shuffle_button = self.device(text="Shuffle play", packageName=self.package_name)
            if shuffle_button.exists:
                shuffle_button.click()
                logger.info("Clicked Shuffle play using text selector")
                time.sleep(5)
                return True

            shuffle_xpath = ('//*[@resource-id="com.google.android.apps.youtube.music:id/bottom_sheet_list"]'
                             '/android.widget.FrameLayout[1]')
            shuffle_element = self.device.xpath(shuffle_xpath)
            if shuffle_element.exists:
                shuffle_element.click()
                logger.info("Clicked shuffle button using XPath")
                return True

            logger.error("Shuffle button not found using any method")
            return False
        except Exception as e:
            logger.error(f"Error with IsoClipboard: {e}")
            return False

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
        """Skip to next track."""
        try:
            next_button = self.device(
                resourceId="com.google.android.apps.youtube.music:id/player_control_next_button"
            )
            if not next_button.exists:
                logger.error("Next track button not found")
                return False

            next_button.click()
            logger.info("Clicked next track button")
            return True

        except Exception as e:
            logger.error(f"Error skipping to next track: {e}")
            return False

    def previous_track(self) -> bool:
        """Go to previous track."""
        try:
            prev_button = self.device(
                resourceId="com.google.android.apps.youtube.music:id/player_control_previous_button"
            )
            if not prev_button.exists:
                logger.error("Previous track button not found")
                return False

            prev_button.click()
            logger.info("Clicked previous track button")
            return True

        except Exception as e:
            logger.error(f"Error going to previous track: {e}")
            return False

    def like_current_song(self) -> bool:
        xpath = (
            '//*[contains(@content-desc, "like this video along with") '
            'and contains(@content-desc, "other people")]/android.view.ViewGroup[1]'
        )

        original_wait_timeout = self.device.wait_timeout
        original_implicit_wait = 0.0

        try:
            short_timeout = 0.5
            self.device.wait_timeout = short_timeout
            self.device.implicitly_wait(short_timeout)

            like_button = self.device.xpath(xpath)
            if like_button.exists:
                try:
                    like_button.click()
                    logger.info("Liked current song via direct XPath click")
                    return True
                except Exception as e:
                    logger.warning(f"Direct XPath click failed: {e}")

            if like_button.exists:
                try:
                    element_info = like_button.info
                    if element_info:
                        bounds = element_info.get('bounds', {})
                        center_x = (bounds.get('left', 0) + bounds.get('right', 0)) // 2
                        center_y = (bounds.get('top', 0) + bounds.get('bottom', 0)) // 2

                        if center_x and center_y:
                            self.device.click(center_x, center_y)
                            logger.info("Liked current song via bounding-box center tap")
                            return True
                except Exception as bbox_err:
                    logger.warning(f"Bounding-box tap failed: {bbox_err}")

            screen_w, screen_h = self.device.window_size()
            fallback1_x = int(0.113 * screen_w)
            fallback1_y = int(0.623 * screen_h)

            try:
                self.device.click(fallback1_x, fallback1_y)
                logger.info(f"Liked current song via fallback coordinates #1: {fallback1_x}, {fallback1_y}")
                return True
            except Exception as e1:
                logger.warning(f"First fallback coordinate tap failed: {e1}")

            # Second fallback coordinates
            fallback2_x = int(0.121 * screen_w)
            fallback2_y = int(0.659 * screen_h)

            try:
                self.device.click(fallback2_x, fallback2_y)
                logger.info(f"Liked current song via fallback coordinates #2: {fallback2_x}, {fallback2_y}")
                return True
            except Exception as e2:
                logger.warning(f"Second fallback coordinate tap failed: {e2}")
                return False

        except Exception as main_err:
            logger.error(f"Error liking current song: {main_err}")
            return False

        finally:
            self.device.wait_timeout = original_wait_timeout
            self.device.implicitly_wait(original_implicit_wait)

    def start_app(self) -> bool:
        try:
            self.device.app_start(self.package_name)
            time.sleep(3)
            return self.is_running()
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