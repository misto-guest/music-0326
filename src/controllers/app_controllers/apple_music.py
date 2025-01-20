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

    def start_app(self) -> bool:
        try:
            self.device.app_start(self.package_name)
            time.sleep(2)

            # Navigate to Library if needed
            library_tab = self.device(resourceId=f"{self.package_name}:id/navigation_library")
            if library_tab.exists:
                library_tab.click()
                time.sleep(1)

            return self.is_running()
        except Exception as e:
            logger.error(f"Error starting Apple Music: {e}")
            return False

    def stop_app(self) -> bool:
        try:
            self.device.app_stop(self.package_name)
            return True
        except Exception as e:
            logger.error(f"Error stopping Apple Music: {e}")
            return False

    def is_running(self) -> bool:
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
            # Try finding the play button by description first
            play_button = self.device(description="Play or pause")
            if not play_button.exists:
                play_button = self.device(resourceId=f"{self.package_name}:id/play_pause_button")

            if not play_button.exists:
                screen_w, screen_h = self.device.window_size()
                play_x = int(0.5 * screen_w)
                play_y = int(0.9 * screen_h)
                self.safe_click(play_x / screen_w, play_y / screen_h, "play/pause button")
                logger.info("Clicked play/pause via coordinates")
                return True

            play_button.click()
            logger.info("Clicked play/pause button")
            return True

        except Exception as e:
            logger.error(f"Error toggling play/pause: {e}")
            return False

    def next_track(self) -> bool:
        """Skip to next track."""
        try:
            next_button = self.device(description="Next track")
            if not next_button.exists:
                next_button = self.device(resourceId=f"{self.package_name}:id/next_button")

            if not next_button.exists:
                screen_w, screen_h = self.device.window_size()
                next_x = int(0.85 * screen_w)
                next_y = int(0.9 * screen_h)
                self.safe_click(next_x / screen_w, next_y / screen_h, "next track button")
                logger.info("Clicked next track via coordinates")
                return True

            next_button.click()
            logger.info("Clicked next track button")
            return True

        except Exception as e:
            logger.error(f"Error skipping to next track: {e}")
            return False

    def previous_track(self) -> bool:
        """Go to previous track."""
        try:
            prev_button = self.device(description="Previous track")
            if not prev_button.exists:
                prev_button = self.device(resourceId=f"{self.package_name}:id/previous_button")

            if not prev_button.exists:
                screen_w, screen_h = self.device.window_size()
                prev_x = int(0.15 * screen_w)
                prev_y = int(0.9 * screen_h)
                self.safe_click(prev_x / screen_w, prev_y / screen_h, "previous track button")
                logger.info("Clicked previous track via coordinates")
                return True

            prev_button.click()
            logger.info("Clicked previous track button")
            return True

        except Exception as e:
            logger.error(f"Error going to previous track: {e}")
            return False

    def like_current_song(self) -> bool:
        """Like the currently playing song."""
        try:
            like_button = self.device(description="Love")
            if not like_button.exists:
                like_button = self.device(description="Add to your library")

            if not like_button.exists:
                like_button = self.device(resourceId=f"{self.package_name}:id/like_button")

            if not like_button.exists:
                screen_w, screen_h = self.device.window_size()
                like_x = int(0.1 * screen_w)
                like_y = int(0.85 * screen_h)
                self.safe_click(like_x / screen_w, like_y / screen_h, "like button")
                logger.info("Clicked like button via coordinates")
                return True

            like_button.click()
            logger.info("Clicked like button")
            return True

        except Exception as e:
            logger.error(f"Error liking current song: {e}")
            return False

    def handle_isoclipboard(self) -> bool:
        """Handle IsoClipboard for Apple Music."""
        try:
            search_tab = self.device(resourceId=f"{self.package_name}:id/navigation_search")
            if not search_tab.exists:
                logger.error("Search tab not found")
                return False

            search_tab.click()
            time.sleep(1)

            search_field = self.device(resourceId=f"{self.package_name}:id/search_box")
            if not search_field.exists:
                logger.error("Search field not found")
                return False

            search_field.click()
            time.sleep(1)

            self.device.press("paste")
            self.device.press("enter")
            time.sleep(2)

            first_result = self.device(resourceId=f"{self.package_name}:id/search_result_item").first()
            if not first_result.exists:
                logger.error("No search results found")
                return False

            first_result.click()
            time.sleep(1)

            return self.play_pause()

        except Exception as e:
            logger.error(f"Error with IsoClipboard: {e}")
            return False