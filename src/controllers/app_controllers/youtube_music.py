# src/controllers/app_controllers/youtube_music.py

import time
from typing import Optional
import uiautomator2 as u2
from src.constants.app_configs import YouTubeMusicConfig
from src.constants.screen_coordinates import YouTubeMusicCoordinates
from src.utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class YouTubeMusicController:
    """Controller for YouTube Music automation."""

    def __init__(self, device: u2.Device):
        """Initialize YouTube Music controller."""
        self.device = device
        self.package_name = YouTubeMusicConfig.PACKAGE_NAME
        self.coordinates = YouTubeMusicCoordinates()
        self.app_name = YouTubeMusicConfig.APP_NAME

    def start_app(self) -> bool:
        """Start YouTube Music application."""
        try:
            self.device.app_start(self.package_name)
            time.sleep(3)
            return self.is_running()
        except Exception as e:
            logger.error(f"Error starting YouTube Music: {e}")
            return False

    def stop_app(self) -> bool:
        """Stop YouTube Music application."""
        try:
            self.device.app_stop(self.package_name)
            return True
        except Exception as e:
            logger.error(f"Error stopping YouTube Music: {e}")
            return False

    def is_running(self) -> bool:
        """Check if YouTube Music is currently running."""
        try:
            return bool(self.device(packageName=self.package_name).exists)
        except Exception as e:
            logger.error(f"Error checking if YouTube Music is running: {e}")
            return False

    def force_stop(self) -> bool:
        """Force stop the app."""
        try:
            self.device.app_stop(self.package_name)
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error force stopping YouTube Music: {e}")
            return False

    def play_pause(self) -> bool:
        """Toggle play/pause state."""
        try:
            # Try to find play button by resource ID first
            play_button = self.device(resourceId=f"{self.package_name}:id/player_control_play_pause_replay_button")
            if play_button.exists:
                play_button.click()
                return True

            # Fallback to coordinates
            coords = self.coordinates.get_all_coordinates()
            self.device.click(*coords['play_pause'])
            return True
        except Exception as e:
            logger.error(f"Error toggling play/pause: {e}")
            return False

    def next_track(self) -> bool:
        """Skip to next track."""
        try:
            next_button = self.device(resourceId=f"{self.package_name}:id/player_control_next_button")
            if next_button.exists:
                next_button.click()
                return True

            coords = self.coordinates.get_all_coordinates()
            self.device.click(*coords['next_track'])
            return True
        except Exception as e:
            logger.error(f"Error skipping to next track: {e}")
            return False

    def previous_track(self) -> bool:
        """Go to previous track."""
        try:
            prev_button = self.device(resourceId=f"{self.package_name}:id/player_control_previous_button")
            if prev_button.exists:
                prev_button.click()
                return True

            coords = self.coordinates.get_all_coordinates()
            self.device.click(*coords['prev_track'])
            return True
        except Exception as e:
            logger.error(f"Error going to previous track: {e}")
            return False

    def like_current_song(self) -> bool:
        """Like the currently playing song."""
        try:
            like_xpath = '//*[@content-desc="like this video along with 0 other people"]/android.view.ViewGroup[1]'
            like_button = self.device.xpath(like_xpath)
            if like_button.exists:
                like_button.click()
                logger.info("Liked current song using XPath")
                return True

            coords = self.coordinates.get_all_coordinates()
            self.device.click(*coords['like_button'])
            logger.info("Liked current song using coordinates")
            return True
        except Exception as e:
            logger.error(f"Error liking current song: {e}")
            return False

    def handle_isoclipboard(self) -> bool:
        """Handle IsoClipboard interaction."""
        try:
            coords = self.coordinates.get_all_coordinates()
            self.device.click(*coords['isoclipboard'])
            time.sleep(3)

            menu_coords = coords['menu_button']
            self.device.click(*menu_coords)
            time.sleep(2)

            # Try to find shuffle button by text first
            shuffle_button = self.device(text="Shuffle play",
                                         packageName=self.package_name)
            if shuffle_button.exists:
                shuffle_button.click()
            else:
                shuffle_coords = coords['shuffle_button']
                self.device.click(*shuffle_coords)

            return True
        except Exception as e:
            logger.error(f"Error handling IsoClipboard: {e}")
            return False