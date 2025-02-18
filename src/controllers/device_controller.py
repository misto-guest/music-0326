# src/controllers/device_controller.py

import time
import logging
from typing import Dict, Optional, List
import uiautomator2 as u2
from src.utils.adb_commands import execute_adb_command
from src.utils.logging_utils import setup_logger
from src.constants.app_configs import MusicApps
from src.controllers.app_controllers.apple_music import AppleMusicController
from src.controllers.app_controllers.youtube_music import YouTubeMusicController
from src.controllers.app_controllers.amazon_music import AmazonMusicController

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
            'youtube_music': YouTubeMusicController(self.device),
            'amazon_music': AmazonMusicController(self.device)
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
            app_type: Type of music app ('apple', 'youtube', or 'amazon')
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

    def get_rotation_settings(self) -> Dict[str, str]:
        """
        Get current rotation settings from the device.

        Returns:
            Dict containing auto_rotate and user_rotation settings
        """
        try:
            auto_rotate = self.device.shell('settings get system accelerometer_rotation').output.strip()
            user_rotation = self.device.shell('settings get system user_rotation').output.strip()

            logger.info(f"Current rotation settings - auto: {auto_rotate}, user: {user_rotation}")
            return {
                'auto_rotate': auto_rotate,
                'user_rotation': user_rotation
            }
        except Exception as e:
            logger.error(f"Error getting rotation settings: {e}")
            return {}

    def set_rotation_settings(self, settings: Dict[str, str]) -> bool:
        """
        Set rotation settings on the device.

        Args:
            settings: Dict containing auto_rotate and user_rotation values

        Returns:
            bool: True if settings were applied successfully
        """
        try:
            if 'auto_rotate' in settings:
                self.device.shell(f'settings put system accelerometer_rotation {settings["auto_rotate"]}')

            if 'user_rotation' in settings:
                self.device.shell(f'settings put system user_rotation {settings["user_rotation"]}')

            # Verify settings were applied
            current_settings = self.get_rotation_settings()
            settings_match = all(
                current_settings.get(key) == value
                for key, value in settings.items()
                if key in current_settings
            )

            if not settings_match:
                logger.error("Failed to apply rotation settings")
                return False

            logger.info("Rotation settings applied successfully")
            return True

        except Exception as e:
            logger.error(f"Error setting rotation settings: {e}")
            return False

    def force_disable_rotation(self) -> bool:
        """
        Force disable device rotation with verification.

        Returns:
            bool: True if rotation was disabled successfully
        """
        try:
            for attempt in range(3):
                self.device.shell('settings put system accelerometer_rotation 0')
                time.sleep(0.5)

                current = self.device.shell('settings get system accelerometer_rotation').output.strip()
                if current == '0':
                    logger.info("Successfully disabled rotation")
                    return True

                if attempt < 2:  # Don't log on last attempt
                    logger.warning(f"Rotation disable attempt {attempt + 1} failed, retrying...")

            logger.error("Failed to disable rotation after 3 attempts")
            return False

        except Exception as e:
            logger.error(f"Error forcing rotation disable: {e}")
            return False

    def verify_rotation_disabled(self) -> bool:
        """
        Verify rotation is disabled and fix if needed.

        Returns:
            bool: True if rotation is confirmed disabled
        """
        try:
            current = self.device.shell('settings get system accelerometer_rotation').output.strip()

            if current != '0':
                logger.warning("Rotation enabled when it should be disabled, forcing disable")
                return self.force_disable_rotation()

            logger.debug("Verified rotation is disabled")
            return True

        except Exception as e:
            logger.error(f"Error verifying rotation: {e}")
            return False

    def restore_rotation_settings(self, settings: Dict[str, str]) -> bool:
        """
        Restore rotation to specified settings.

        Args:
            settings: Dict containing desired rotation settings

        Returns:
            bool: True if settings were restored successfully
        """
        return self.set_rotation_settings(settings)

    def ensure_screen_active(self) -> bool:
        """
        Ensure the device screen is on and responsive.

        Returns:
            bool: True if screen is active and responsive
        """
        try:
            # Get initial screen state
            screen_state = self.device.info.get('screenOn')
            logger.info(f"Initial screen state: {screen_state}")

            if not screen_state:
                # Try to wake up the screen
                self.device.press("power")
                time.sleep(2)

                # Check if screen is now on
                screen_state = self.device.info.get('screenOn')
                if not screen_state:
                    logger.error("Failed to activate screen")
                    return False

            # Verify screen is responsive by checking for UI elements
            if not self._verify_screen_responsive():
                logger.error("Screen is on but not responsive")
                return False

            logger.info("Screen is active and responsive")
            return True

        except Exception as e:
            logger.error(f"Error ensuring screen active: {e}")
            return False

    def _verify_screen_responsive(self) -> bool:
        """
        Verify screen is responsive by checking for UI elements.

        Returns:
            bool: True if screen is responsive
        """
        try:
            # Try to press HOME to exit any lock screen
            self.device.press("home")
            time.sleep(1)

            # Check if any clickable elements exist
            if self.device(clickable=True).exists:
                return True

            # Additional check: try to read screen state again
            screen_info = self.device.info
            screen_on = screen_info.get('screenOn')
            screen_unlocked = screen_info.get('screenUnlocked', True)  # Assume unlocked if not present

            return bool(screen_on and screen_unlocked)

        except Exception as e:
            logger.error(f"Error verifying screen responsiveness: {e}")
            return False

    def set_screen_timeout(self, timeout_ms: int = 1800000) -> bool:
        """
        Set screen timeout duration.

        Args:
            timeout_ms: Screen timeout in milliseconds (default 30 minutes)

        Returns:
            bool: True if timeout was set successfully
        """
        try:
            # Set screen timeout
            self.device.shell(f'settings put system screen_off_timeout {timeout_ms}')

            # Verify setting was applied
            current_timeout = self.device.shell('settings get system screen_off_timeout')
            if str(timeout_ms) not in str(current_timeout):
                logger.error(f"Failed to set screen timeout to {timeout_ms}")
                return False

            logger.info(f"Screen timeout set to {timeout_ms}ms")
            return True

        except Exception as e:
            logger.error(f"Error setting screen timeout: {e}")
            return False

    def set_stay_on_while_plugged_in(self, enabled: bool = True) -> bool:
        """
        Set whether screen stays on while device is plugged in.

        Args:
            enabled: True to keep screen on while plugged in

        Returns:
            bool: True if setting was applied successfully
        """
        try:
            value = "3" if enabled else "0"
            self.device.shell(f'settings put global stay_on_while_plugged_in {value}')

            # Verify setting
            current = self.device.shell('settings get global stay_on_while_plugged_in')
            if value not in str(current):
                logger.error(f"Failed to set stay_on_while_plugged_in to {value}")
                return False

            status = "enabled" if enabled else "disabled"
            logger.info(f"Stay on while plugged in {status}")
            return True

        except Exception as e:
            logger.error(f"Error setting stay on while plugged in: {e}")
            return False

    def setup_screen_settings(self) -> bool:
        """
        Configure all screen-related settings for optimal operation.

        Returns:
            bool: True if all settings were applied successfully
        """
        try:
            # Ensure screen is active first
            if not self.ensure_screen_active():
                return False

            # Set 30-minute screen timeout
            if not self.set_screen_timeout(1800000):
                return False

            # Enable stay on while plugged in
            if not self.set_stay_on_while_plugged_in(True):
                return False

            logger.info("All screen settings configured successfully")
            return True

        except Exception as e:
            logger.error(f"Error setting up screen settings: {e}")
            return False