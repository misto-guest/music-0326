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
                self.device.shell('am start -n com.android.settings/.Settings')  # Open settings as a fallback
                return False

            time.sleep(3)

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

            shuffle_element = self.device.xpath(
                '//*[@resource-id="com.google.android.apps.youtube.music:id/bottom_sheet_list"]'
                '/android.widget.FrameLayout[1]'
            )

            if not shuffle_element.exists:
                logger.info("Trying to find shuffle button by text")
                shuffle_element = self.device(text="Shuffle play",
                                              packageName=self.package_name)

            if not shuffle_element.exists:
                logger.error("Shuffle button not found using any method")
                return False

            shuffle_element.click()
            logger.info("Clicked shuffle button")
            time.sleep(2)
            return True

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