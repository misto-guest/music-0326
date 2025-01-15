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

    def handle_isoclipboard(self) -> bool:
        """Handle IsoClipboard interaction."""
        try:
            # Start IsoClipboard app
            self.device.app_start(self.isoclipboard_package)
            time.sleep(2)

            # Click FETCH button
            fetch_button = self.device(resourceId=f"{self.isoclipboard_package}:id/buttonFetchUrl4")
            if not fetch_button.exists:
                logger.error("FETCH button not found")
                return False
            fetch_button.click()
            logger.info("Clicked FETCH")
            time.sleep(3)

            # Click the specific YouTube Music element using XPath
            youtube_element = self.device.xpath(
                '//*[@resource-id="com.google.android.apps.youtube.music:id/elements_container"]'
                '/android.view.ViewGroup[1]/android.view.ViewGroup[5]/android.widget.ImageView[1]'
            )
            if not youtube_element.exists:
                logger.error("YouTube Music element not found")
                return False

            youtube_element.click()
            logger.info("Clicked YouTube Music element")
            time.sleep(3)

            # Find and click the shuffle button using new XPath
            shuffle_element = self.device.xpath(
                '//*[@resource-id="com.google.android.apps.youtube.music:id/bottom_sheet_list"]'
                '/android.widget.FrameLayout[1]'
            )

            if shuffle_element.exists:
                shuffle_element.click()
                logger.info("Clicked shuffle button")
                return True

            # Fallback to coordinates if XPath fails
            screen_info = self.device.window_size()
            shuffle_x = int(0.55 * screen_info[0])
            shuffle_y = int(0.682 * screen_info[1])
            self.device.click(shuffle_x, shuffle_y)
            logger.info(f"Clicked shuffle button using coordinates at: {shuffle_x}, {shuffle_y}")
            return True

        except Exception as e:
            logger.error(f"Error with IsoClipboard: {e}")
            return False

    def play_pause(self) -> bool:
        """Toggle play/pause state."""
        try:
            play_button = self.device.xpath(
                '//android.widget.ImageButton[@content-desc="Play" or @content-desc="Pause"]'
            )
            if play_button.exists:
                play_button.click()
                logger.info("Toggled play/pause state")
                return True
            return False
        except Exception as e:
            logger.error(f"Error toggling play/pause: {e}")
            return False

    def next_track(self) -> bool:
        """Skip to next track."""
        try:
            next_button = self.device(
                resourceId="com.google.android.apps.youtube.music:id/player_control_next_button"
            )
            if next_button.exists:
                next_button.click()
                logger.info("Clicked next track button using resource ID")
                return True

            # Fallback to coordinates
            screen_info = self.device.window_size()
            next_x = int(0.722 * screen_info[0])
            next_y = int(0.807 * screen_info[1])
            self.device.click(next_x, next_y)
            logger.info(f"Clicked next track using coordinates at: {next_x}, {next_y}")
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
            if prev_button.exists:
                prev_button.click()
                logger.info("Clicked previous track button using resource ID")
                return True

            # Fallback to coordinates
            screen_info = self.device.window_size()
            prev_x = int(0.27 * screen_info[0])
            prev_y = int(0.789 * screen_info[1])
            self.device.click(prev_x, prev_y)
            logger.info(f"Clicked previous track using coordinates at: {prev_x}, {prev_y}")
            return True

        except Exception as e:
            logger.error(f"Error going to previous track: {e}")
            return False

    def like_current_song(self) -> bool:
        """Like the currently playing song."""
        try:
            like_button = self.device.xpath(
                '//*[@content-desc="like this video along with 0 other people"]/'
                'android.view.ViewGroup[1]'
            )
            if like_button.exists:
                like_button.click()
                logger.info("Liked current song")
                return True
            return False
        except Exception as e:
            logger.error(f"Error liking current song: {e}")
            return False

    # Other required methods from BaseController
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