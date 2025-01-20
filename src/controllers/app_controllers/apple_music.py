# src/controllers/app_controllers/apple_music.py

import time
from typing import Optional
import uiautomator2 as u2
from src.controllers.base_controller import BaseController
from src.constants.app_configs import AppleMusicConfig
from src.utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class AppleMusicController(BaseController):
    """Controller for Apple Music automation."""

    def __init__(self, device: u2.Device):
        """Initialize Apple Music controller."""
        super().__init__(device)
        self.package_name = AppleMusicConfig.PACKAGE_NAME
        self.app_name = AppleMusicConfig.APP_NAME
        self.isoclipboard_package = "com.example.isolatedclipboard"

    def start_app(self) -> bool:
        """Start Apple Music app."""
        try:
            self.device.app_start(self.package_name)
            time.sleep(2)
            return self.is_running()
        except Exception as e:
            logger.error(f"Error starting Apple Music: {e}")
            return False

    def stop_app(self) -> bool:
        """Stop Apple Music app."""
        try:
            self.device.app_stop(self.package_name)
            return True
        except Exception as e:
            logger.error(f"Error stopping Apple Music: {e}")
            return False

    def is_running(self) -> bool:
        """Check if Apple Music is running."""
        try:
            return bool(self.device(packageName=self.package_name).exists)
        except Exception as e:
            logger.error(f"Error checking if Apple Music is running: {e}")
            return False

    def force_stop(self) -> bool:
        """Force stop Apple Music."""
        try:
            self.device.app_stop(self.package_name)
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error force stopping Apple Music: {e}")
            return False

    def play_pause(self) -> bool:
        """Toggle play/pause state."""
        try:
            # Using the exact resource ID
            play_button = self.device.xpath('//*[@resource-id="com.apple.android.music:id/play_pause"]')
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
            # Using the exact resource ID
            next_button = self.device.xpath('//*[@resource-id="com.apple.android.music:id/next_fast_forward"]')
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
            # Using the exact resource ID
            prev_button = self.device.xpath('//*[@resource-id="com.apple.android.music:id/previous_rewind"]')
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
            # Using the exact resource ID
            like_button = self.device.xpath('//*[@resource-id="com.apple.android.music:id/list_favorite_icon"]')
            if not like_button.exists:
                logger.error("Like button not found")
                return False

            like_button.click()
            logger.info("Clicked like button")
            return True

        except Exception as e:
            logger.error(f"Error liking current song: {e}")
            return False

    def shuffle(self) -> bool:
        """Toggle shuffle mode."""
        try:
            # Using the exact resource ID
            shuffle_button = self.device.xpath('//*[@resource-id="com.apple.android.music:id/button_shuffle"]')
            if not shuffle_button.exists:
                logger.error("Shuffle button not found")
                return False

            shuffle_button.click()
            logger.info("Clicked shuffle button")
            return True

        except Exception as e:
            logger.error(f"Error toggling shuffle: {e}")
            return False

    def handle_isoclipboard(self) -> bool:
        """Handle IsoClipboard for Apple Music."""
        try:
            # Start IsoClipboard app
            self.device.app_start("com.example.isolatedclipboard")
            time.sleep(2)

            # Click FETCH button using correct resource ID
            fetch_button = self.device.xpath('//*[@resource-id="com.example.isolatedclipboard:id/buttonFetchUrl2"]')
            if not fetch_button.exists:
                logger.error("FETCH button not found")
                return False

            fetch_button.click()
            logger.info("Clicked FETCH button")
            time.sleep(2)

            # Check if already in Apple Music
            if not self.is_running():
                logger.info("Starting Apple Music")
                self.start_app()
                time.sleep(2)

            # Navigate to Search tab if needed
            search_tab = self.device.xpath('//*[@resource-id="com.apple.android.music:id/navigation_search"]')
            if search_tab.exists:
                search_tab.click()
                time.sleep(1)

            # Click search field
            search_field = self.device.xpath('//*[@resource-id="com.apple.android.music:id/search_box"]')
            if not search_field.exists:
                logger.error("Search field not found")
                return False

            search_field.click()
            time.sleep(1)

            # Paste and search
            self.device.press("paste")
            time.sleep(0.5)
            self.device.press("enter")
            time.sleep(2)

            # Click first result
            first_result = self.device.xpath('//*[@resource-id="com.apple.android.music:id/search_result_item"]')
            if not first_result.exists:
                logger.error("No search results found")
                return False

            first_result.click()
            time.sleep(2)

            # Ensure playback starts
            return self.play_pause()

        except Exception as e:
            logger.error(f"Error with IsoClipboard: {e}")
            return False