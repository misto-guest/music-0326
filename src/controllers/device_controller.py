# src/controllers/device_controller.py

import logging
from typing import Dict, Optional, List
import uiautomator2 as u2
from src.utils.adb_commands import execute_adb_command
from src.utils.logging_utils import setup_logger
from src.constants.app_configs import MusicApps
from src.controllers.app_controllers.apple_music import AppleMusicController
from src.controllers.app_controllers.youtube_music import YouTubeMusicController

logger = setup_logger(__name__)


class DeviceController:
    """Main controller for device and app management."""

    def __init__(self, device_id: str):
        self.device_id = device_id
        self.device = u2.connect(device_id)
        self.music_apps = MusicApps.REGISTERED_APPS
        self.base_packages = MusicApps.BASE_PACKAGES
        self._initialize_app_controllers()

    def _initialize_app_controllers(self):
        """Initialize controllers for each music app."""
        self.app_controllers = {
            'apple_music': AppleMusicController(self.device),
            'youtube_music': YouTubeMusicController(self.device)
        }

    def get_app_name_from_package(self, package_name: str) -> str:
        """Get display name for a package, handling clones appropriately."""
        if package_name in self.music_apps:
            return self.music_apps[package_name]

        for base_pkg, base_name in self.base_packages.items():
            if package_name.startswith(base_pkg):
                return f"{base_name} Clone (Package: {package_name})"

        return f"Unknown App (Package: {package_name})"

    def check_running_music_apps(self) -> Optional[str]:
        """Check which music apps are running."""
        try:
            running_apps = []
            for controller in self.app_controllers.values():
                if controller.is_running():
                    running_apps.append(controller.app_name)

            if running_apps:
                logger.info("Running music apps: %s", running_apps)
            else:
                logger.info("No music apps running")

            return running_apps
        except Exception as e:
            logger.error("Error checking running apps: %s", e)
            return None

    def close_music_recent_apps(self):
        """Close only music-related recent apps."""
        try:
            for controller in self.app_controllers.values():
                if controller.is_running():
                    logger.info(f"Closing {controller.app_name}")
                    controller.stop_app()

            self.check_running_music_apps()
        except Exception as e:
            logger.error("Error closing music apps: %s", e)

    def force_stop_music_apps(self):
        """Force stop all music apps."""
        try:
            for controller in self.app_controllers.values():
                logger.info(f"Force stopping {controller.app_name}")
                controller.force_stop()

            self.check_running_music_apps()
        except Exception as e:
            logger.error("Error force stopping apps: %s", e)

    def control_isoclipboard(self, app_type: str = "youtube"):
        """Control IsoClipboard app and handle app selection."""
        try:
            # Get the appropriate controller
            controller = self.app_controllers.get(f"{app_type}_music")
            if not controller:
                logger.error(f"No controller found for app type: {app_type}")
                return

            # Start IsoClipboard and perform actions
            controller.handle_isoclipboard()
        except Exception as e:
            logger.error(f"Error with isoclipboard: {e}")

    def control_music_playback(self, app_type: str, action: str):
        """
        Control music playback for specified app.

        Args:
            app_type: Type of music app ('apple' or 'youtube')
            action: Playback action ('play', 'pause', 'next', 'previous', 'like')
        """
        try:
            controller = self.app_controllers.get(f"{app_type}_music")
            if not controller:
                logger.error(f"No controller found for app type: {app_type}")
                return

            actions = {
                'play': controller.play_pause,
                'pause': controller.play_pause,
                'next': controller.next_track,
                'previous': controller.previous_track,
                'like': controller.like_current_song
            }

            if action in actions:
                actions[action]()
            else:
                logger.error(f"Unknown action: {action}")
        except Exception as e:
            logger.error(f"Error controlling playback: {e}")