# src/controllers/app_controllers/apple_music.py

import time
from typing import Optional
import uiautomator2 as u2
from src.controllers.base_controller import BaseController
from src.constants.app_configs import AppleMusicConfig
from src.constants.screen_coordinates import AppleMusicCoordinates
from src.utils.adb_commands import execute_adb_command
from src.utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class AppleMusicController:
    """Controller for Apple Music automation."""

    def __init__(self, device: u2.Device):
        """Initialize Apple Music controller."""
        self.device = device
        self.package_name = AppleMusicConfig.PACKAGE_NAME
        self.coordinates = AppleMusicCoordinates()
        self.app_name = AppleMusicConfig.APP_NAME

    def start_app(self) -> bool:
        """Start Apple Music application."""
        try:
            self.device.app_start(self.package_name)
            time.sleep(3)  # Wait for app to initialize
            return self.is_running()
        except Exception as e:
            logger.error(f"Error starting Apple Music: {e}")
            return False

    def stop_app(self) -> bool:
        """Stop Apple Music application."""
        try:
            self.device.app_stop(self.package_name)
            return True
        except Exception as e:
            logger.error(f"Error stopping Apple Music: {e}")
            return False

    def is_running(self) -> bool:
        """Check if Apple Music is currently running."""
        try:
            return bool(self.device(packageName=self.package_name).exists)
        except Exception as e:
            logger.error(f"Error checking if Apple Music is running: {e}")
            return False

    def force_stop(self) -> bool:
        """Force stop the app."""
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
            coords = self.coordinates.get_all_coordinates()
            self.device.click(*coords['play_pause'])
            return True
        except Exception as e:
            logger.error(f"Error toggling play/pause: {e}")
            return False

    def next_track(self) -> bool:
        """Skip to next track."""
        try:
            coords = self.coordinates.get_all_coordinates()
            self.device.click(*coords['next_track'])
            return True
        except Exception as e:
            logger.error(f"Error skipping to next track: {e}")
            return False

    def previous_track(self) -> bool:
        """Go to previous track."""
        try:
            coords = self.coordinates.get_all_coordinates()
            self.device.click(*coords['prev_track'])
            return True
        except Exception as e:
            logger.error(f"Error going to previous track: {e}")
            return False

    def like_current_song(self) -> bool:
        """Like the currently playing song."""
        try:
            coords = self.coordinates.get_all_coordinates()
            self.device.click(*coords['like_button'])
            return True
        except Exception as e:
            logger.error(f"Error liking current song: {e}")
            return False

    def handle_isoclipboard(self) -> bool:
        """Handle IsoClipboard interaction."""
        try:
            coords = self.coordinates.get_all_coordinates()
            self.device.click(*coords['isoclipboard'])
            time.sleep(4)
            return True
        except Exception as e:
            logger.error(f"Error handling IsoClipboard: {e}")
            return False