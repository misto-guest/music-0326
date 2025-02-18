# src/controllers/app_coordination.py

import time
import threading
from typing import Dict, Optional, Any
from src.utils.logging_utils import setup_logger
from src.controllers.device_controller import DeviceController
from src.controllers.mutex_mixin import MutexMixin

logger = setup_logger(__name__)


class AppCoordinationManager(MutexMixin):
    """
    Manages coordination and safe transitions between multiple music apps.
    Inherits from MutexMixin to ensure thread-safe operations.
    """

    def __init__(self, device_controller: DeviceController):
        """
        Initialize the coordination manager.

        Args:
            device_controller: The main device controller instance
        """
        super().__init__()
        self.device_controller = device_controller
        self.active_app: Optional[str] = None
        self.min_transition_delay = 3  # seconds
        self.last_transition_time = 0
        self._app_states: Dict[str, Dict[str, Any]] = {}

    @property
    def app_states(self) -> Dict[str, Dict[str, Any]]:
        """Thread-safe access to app states."""
        with self._app_mutex:
            return self._app_states.copy()

    def _ensure_safe_delay(self) -> None:
        """Ensure minimum delay between app transitions."""
        current_time = time.time()
        time_since_last = current_time - self.last_transition_time
        if time_since_last < self.min_transition_delay:
            time.sleep(self.min_transition_delay - time_since_last)
        self.last_transition_time = time.time()

    @MutexMixin.with_device_lock
    def prepare_app_transition(self, target_app: str, current_state: Optional[Dict] = None) -> bool:
        """
        Safely prepare for transitioning to a new app.

        Args:
            target_app: Name of the app to transition to
            current_state: Optional dict containing desired state information

        Returns:
            bool: True if transition preparation was successful
        """
        try:
            self._ensure_safe_delay()

            # Store rotation state before transition
            initial_rotation = self.device_controller.get_rotation_settings()

            # Force stop any interfering apps
            self._force_stop_interfering_apps()

            # Ensure device is in correct state
            if not self._ensure_device_ready():
                logger.error(f"Device not ready for {target_app} transition")
                return False

            # Get and verify target app controller
            controller = self.device_controller.app_controllers.get(target_app)
            if not controller:
                logger.error(f"No controller found for {target_app}")
                return False

            # Enhanced app preparation with retries
            success = False
            for attempt in range(3):
                if controller.prepare_for_action():
                    success = True
                    break
                if attempt < 2:  # Don't sleep after last attempt
                    time.sleep(2)

            if not success:
                logger.error(f"Failed to prepare {target_app} after 3 attempts")
                return False

            # Verify playback state if needed
            if current_state and current_state.get('should_be_playing'):
                if not self._verify_playback_state(controller):
                    logger.warning(f"Playback state verification failed for {target_app}")
                    # Attempt recovery
                    controller.ensure_playing()

            # Update app state
            with self._app_mutex:
                self._app_states[target_app] = {
                    'last_transition': time.time(),
                    'state': current_state or {}
                }

            # Restore rotation settings
            self._restore_rotation_settings(initial_rotation)

            self.active_app = target_app
            return True

        except Exception as e:
            logger.error(f"Error during app transition to {target_app}: {e}")
            return False

    def _force_stop_interfering_apps(self) -> None:
        """Force stop any apps that might interfere with transitions."""
        interfering_packages = [
            "com.example.isolatedclipboard"  # Add other packages if needed
        ]

        for package in interfering_packages:
            try:
                self.device_controller.device.app_stop(package)
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error stopping {package}: {e}")

    def _ensure_device_ready(self) -> bool:
        """Ensure device is in correct state for app transitions."""
        try:
            # Ensure screen is on
            if not self.device_controller.ensure_screen_active():
                return False

            # Disable rotation
            self.device_controller.device.shell('settings put system accelerometer_rotation 0')

            # Verify internet connectivity
            if not self._check_internet_connectivity():
                logger.warning("Internet connectivity issues detected")
                return False

            return True

        except Exception as e:
            logger.error(f"Error ensuring device ready: {e}")
            return False

    def _check_internet_connectivity(self) -> bool:
        """Check if device has internet connectivity."""
        try:
            result = self.device_controller.device.shell(
                'ping -c 1 8.8.8.8 | grep "1 received"'
            )
            return '1 received' in str(result)
        except Exception:
            return False

    def _verify_playback_state(self, controller: Any) -> bool:
        """Verify app is in correct playback state."""
        try:
            # Check if app is responding
            if not controller.is_running():
                return False

            # For apps with play state detection
            if hasattr(controller, 'check_play_state'):
                return controller.check_play_state()

            # Fallback verification
            return self._verify_media_session(controller.package_name)

        except Exception as e:
            logger.error(f"Error verifying playback state: {e}")
            return False

    def _verify_media_session(self, package_name: str) -> bool:
        """Verify media session state for an app."""
        try:
            cmd = f"dumpsys media_session | grep -A 5 {package_name}"
            result = self.device_controller.device.shell(cmd)

            # Parse media session output
            if "state=3" in result or "PlaybackState {state=3" in result:
                return True
            return False

        except Exception as e:
            logger.error(f"Error checking media session: {e}")
            return False

    def _restore_rotation_settings(self, settings: Dict[str, str]) -> None:
        """Restore rotation settings to previous state."""
        try:
            if 'auto_rotate' in settings:
                self.device_controller.device.shell(
                    f'settings put system accelerometer_rotation {settings["auto_rotate"]}'
                )
            if 'user_rotation' in settings:
                self.device_controller.device.shell(
                    f'settings put system user_rotation {settings["user_rotation"]}'
                )
        except Exception as e:
            logger.error(f"Error restoring rotation settings: {e}")

    @MutexMixin.with_app_lock
    def handle_action_failure(self, app_name: str, action: str, error: Optional[Exception] = None) -> bool:
        """
        Handle failed actions with recovery attempts.

        Args:
            app_name: Name of the failed app
            action: The action that failed
            error: Optional exception that caused the failure

        Returns:
            bool: True if recovery was successful
        """
        try:
            logger.warning(f"Action '{action}' failed for {app_name}: {error}")

            controller = self.device_controller.app_controllers.get(app_name)
            if not controller:
                return False

            # Force app restart if needed
            if error and "not responding" in str(error).lower():
                controller.force_stop()
                time.sleep(2)
                return controller.start_app()

            # Try to recover playback state
            if "playback" in str(action).lower():
                return controller.ensure_playing()

            return False

        except Exception as e:
            logger.error(f"Error in failure recovery for {app_name}: {e}")
            return False

    def get_app_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get current status of all managed apps.

        Returns:
            Dict containing status information for each app
        """
        status = {}
        for app_name, controller in self.device_controller.app_controllers.items():
            try:
                is_running = controller.is_running()
                is_playing = (hasattr(controller, 'check_play_state') and
                              controller.check_play_state())

                status[app_name] = {
                    'running': is_running,
                    'playing': is_playing,
                    'is_active': (self.active_app == app_name),
                    'last_state': self.app_states.get(app_name, {})
                }
            except Exception as e:
                logger.error(f"Error getting status for {app_name}: {e}")
                status[app_name] = {'error': str(e)}

        return status