# src/controllers/app_controllers/apple_music.py

import time
from typing import Optional, Dict
import uiautomator2 as u2
from src.controllers.base_controller import BaseController
from src.controllers.mixins.popup_monitor import PopupMonitorMixin
from src.constants.app_configs import AppleMusicConfig
from src.utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class AppleMusicController(BaseController, PopupMonitorMixin):
    """Controller for Apple Music automation with popup monitoring."""

    def __init__(self, device: u2.Device):
        """Initialize Apple Music controller."""
        super().__init__(device)
        PopupMonitorMixin.__init__(self)
        self.package_name = AppleMusicConfig.PACKAGE_NAME
        self.app_name = AppleMusicConfig.APP_NAME
        self.isoclipboard_package = "com.example.isolatedclipboard"

        # Register apps for monitoring
        self.register_app_for_monitoring("Apple Music")
        self.register_app_for_monitoring("IsoClipboard")

        # Start popup monitor
        self.start_popup_monitor()

        # Set up screen settings during initialization
        if not self.setup_screen_settings():
            logger.warning("Failed to set up screen settings during initialization")

    def __del__(self):
        """Cleanup when controller is deleted."""
        try:
            self.stop_popup_monitor()
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")

    def setup_screen_settings(self) -> bool:
        """Setup screen timeout and stay-on settings."""
        try:
            logger.info("Setting up screen settings")
            # Set longer screen timeout (30 minutes)
            self.device.shell('settings put system screen_off_timeout 1800000')
            # Keep screen on while plugged in
            self.device.shell('settings put global stay_on_while_plugged_in 3')
            # Verify settings
            timeout = self.device.shell('settings get system screen_off_timeout')
            if '1800000' in str(timeout):
                logger.info("Screen settings configured successfully")
                return True
            else:
                logger.error("Failed to verify screen settings")
                return False
        except Exception as e:
            logger.error(f"Error setting up screen settings: {e}")
            return False

    def unlock_screen(self) -> bool:
        """Unlock screen without using power button."""
        try:
            logger.info("Starting screen unlock sequence")
            # Use swipe directly to wake and unlock
            self.device.swipe(540, 1800, 540, 900)
            time.sleep(0.5)

            # Verify unlock was successful
            if self.device(resourceId="android:id/statusBarBackground").exists:
                logger.info("Screen unlocked successfully")
                return True

            # Try using KEYCODE_WAKEUP if first attempt failed
            logger.warning("First unlock attempt failed, trying with KEYCODE_WAKEUP")
            self.device.shell('input keyevent KEYCODE_WAKEUP')
            time.sleep(0.1)
            self.device.swipe(540, 1800, 540, 900)

            if self.device(clickable=True).exists:
                logger.info("Screen appears to be unlocked (found clickable elements)")
                return True

            logger.error("Failed to unlock screen")
            return False
        except Exception as e:
            logger.error(f"Error during screen unlock: {e}")
            return False

    def ensure_screen_active(self) -> bool:
        """Ensure device screen is active."""
        try:
            device_info = self.device.info
            screen_state = device_info.get('screenState') if device_info else None
            logger.info(f"Current screen state: {screen_state}")
            return self.unlock_screen()
        except Exception as e:
            logger.error(f"Error ensuring screen active: {e}")
            return self.unlock_screen()  # Try unlock as fallback

    def check_internet_connection(self, max_retries: int = 5, delay: int = 2) -> bool:
        """Check internet connection using netstat."""
        for attempt in range(max_retries):
            try:
                netstat_check = self.device.shell('netstat -n | grep ESTABLISHED | grep -E "^tcp6.*::ffff:|^tcp[^6]"')
                if getattr(netstat_check, 'exit_code', 0) != 0:
                    logger.warning(f"Failed to get TCP connections (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue

                output = str(getattr(netstat_check, 'output', netstat_check)).strip()
                if not output:
                    logger.warning(f"No TCP connections found (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue

                connections = output.split('\n')
                logger.info(f"Found {len(connections)} TCP connections")
                return True
            except Exception as e:
                logger.error(f"Error checking internet connection: {e}")
                time.sleep(delay)
        return False

    def prepare_for_action(self) -> bool:
        """Prepare device for performing an action."""
        try:
            if not self.ensure_screen_active():
                logger.error("Failed to ensure screen active before action")
                return False

            # Clear any pending restart flags
            if self.needs_restart("Apple Music"):
                logger.info("Restarting Apple Music after force-close")
                self.clear_restart_flag("Apple Music")
                time.sleep(2)

            # Bring app to foreground
            self.manage_window_state(minimize=False)
            time.sleep(1)

            if not self.is_running():
                logger.error("App not in foreground after preparation")
                return False

            return True
        except Exception as e:
            logger.error(f"Error preparing for action: {e}")
            return False

    def manage_window_state(self, minimize: bool = True) -> bool:
        """Manage Apple Music window state."""
        try:
            if minimize:
                self.device.press('home')
                time.sleep(1)
            else:
                self.device.app_start(self.package_name)
                time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Failed to manage window state: {e}")
            return False

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
            time.sleep(1)
            # Verify app is actually stopped
            if self.is_running():
                logger.warning("App still running after stop attempt, trying force-stop")
                return self.force_stop()
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
            logger.info("Attempting play/pause...")

            if not self.prepare_for_action():
                if self.needs_restart("Apple Music"):
                    logger.info("Retrying after force-close")
                    self.clear_restart_flag("Apple Music")
                    time.sleep(2)
                    if not self.prepare_for_action():
                        return False
                else:
                    return False

            play_button = self.device.xpath('//*[@resource-id="com.apple.android.music:id/play_pause"]')
            if not play_button.exists:
                logger.error("Play/pause button not found")
                return False

            play_button.click()
            logger.info("Clicked play/pause button")
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error toggling play/pause: {e}")
            return False

    def next_track(self) -> bool:
        """Skip to next track."""
        try:
            logger.info("Attempting next track...")

            if not self.prepare_for_action():
                if self.needs_restart("Apple Music"):
                    logger.info("Retrying after force-close")
                    self.clear_restart_flag("Apple Music")
                    time.sleep(2)
                    if not self.prepare_for_action():
                        return False
                else:
                    return False

            next_button = self.device.xpath('//*[@resource-id="com.apple.android.music:id/next_fast_forward"]')
            if not next_button.exists:
                logger.error("Next track button not found")
                return False

            next_button.click()
            logger.info("Clicked next track button")
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Error skipping to next track: {e}")
            return False

    def previous_track(self) -> bool:
        """Go to previous track."""
        try:
            logger.info("Attempting previous track...")

            if not self.prepare_for_action():
                if self.needs_restart("Apple Music"):
                    logger.info("Retrying after force-close")
                    self.clear_restart_flag("Apple Music")
                    time.sleep(2)
                    if not self.prepare_for_action():
                        return False
                else:
                    return False

            prev_button = self.device.xpath('//*[@resource-id="com.apple.android.music:id/previous_rewind"]')
            if not prev_button.exists:
                logger.error("Previous track button not found")
                return False

            prev_button.click()
            logger.info("Clicked previous track button")
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Error going to previous track: {e}")
            return False

    def like_current_song(self) -> bool:
        """Like the currently playing song."""
        try:
            logger.info("Starting like song action...")

            if not self.prepare_for_action():
                if self.needs_restart("Apple Music"):
                    logger.info("Retrying after force-close")
                    self.clear_restart_flag("Apple Music")
                    time.sleep(2)
                    if not self.prepare_for_action():
                        return False
                else:
                    return False

            like_button = self.device.xpath('//*[@resource-id="com.apple.android.music:id/list_favorite_icon"]')
            if not like_button.exists:
                logger.error("Like button not found")
                return False

            like_button.click()
            logger.info("Clicked like button")
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Error liking current song: {e}")
            return False

    def handle_isoclipboard(self) -> bool:
        """Handle IsoClipboard for Apple Music."""
        try:
            # Start IsoClipboard
            self.device.app_start(self.isoclipboard_package)
            time.sleep(2)

            # Clear any pending restart flags
            if self.needs_restart("IsoClipboard"):
                logger.info("Restarting IsoClipboard after force-close")
                self.clear_restart_flag("IsoClipboard")
                time.sleep(2)
                self.device.app_start(self.isoclipboard_package)
                time.sleep(2)

            # Click FETCH button
            fetch_button = self.device.xpath('//*[@resource-id="com.example.isolatedclipboard:id/buttonFetchUrl2"]')
            if not fetch_button.exists:
                logger.error("FETCH button not found")
                return False

            fetch_button.click()
            logger.info("Clicked FETCH button")
            time.sleep(15)

            # Handle shuffle
            if not self._handle_shuffle_and_miniplayer():
                return False

            return True
        except Exception as e:
            logger.error(f"Error with IsoClipboard: {e}")
            return False

    def _handle_shuffle_and_miniplayer(self) -> bool:
        """Handle shuffle button and miniplayer interaction."""
        try:
            # Click shuffle button
            shuffle_button = self.device.xpath('//*[@resource-id="com.apple.android.music:id/button_shuffle"]')
            if not shuffle_button.exists:
                logger.error("Shuffle button not found")
                return False

            shuffle_button.click()
            logger.info("Clicked shuffle button")
            time.sleep(3)

            # Try multiple miniplayer selectors
            miniplayer_selectors = [
                '//*[@resource-id="com.apple.android.music:id/miniplayer_shareplay_container"]',
                '//*[@resource-id="com.apple.android.music:id/mini_player"]',
                '//*[contains(@resource-id, "miniplayer")]'
            ]

            for selector in miniplayer_selectors:
                miniplayer = self.device.xpath(selector)
                if miniplayer.exists:
                    miniplayer.click()
                    logger.info(f"Clicked miniplayer using selector: {selector}")
                    time.sleep(1)
                    return True

            logger.error("Miniplayer not found after trying multiple selectors")
            return False
        except Exception as e:
            logger.error(f"Error handling shuffle and miniplayer: {e}")
            return False