import time
from typing import Optional, Callable
import uiautomator2 as u2
from functools import wraps
from src.controllers.base_controller import BaseController
from src.constants.app_configs import AppleMusicConfig
from src.utils.logging_utils import setup_logger

logger = setup_logger(__name__)


def handle_unresponsive_alert(self) -> bool:
    """Handle 'Apple Music isn't responding' alert if present."""
    try:
        alert_title = self.device.xpath('//*[@resource-id="android:id/alertTitle"]')
        if alert_title.exists:
            close_button = self.device.xpath('//*[@resource-id="android:id/aerr_close"]')
            if close_button.exists:
                close_button.click()
                time.sleep(1)
                return True
        return False
    except Exception as e:
        logger.error(f"Error handling unresponsive alert: {e}")
        return False

def with_error_recovery(func: Callable) -> Callable:
    """Decorator to add error recovery for Apple Music actions."""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        max_retries = 2
        retry_count = 0

        while retry_count <= max_retries:
            # Check for and handle unresponsive alert before action
            self.handle_unresponsive_alert()

            result = func(self, *args, **kwargs)
            if result:
                return True

            logger.warning(f"Apple Music action {func.__name__} failed, attempt {retry_count + 1}")

            try:
                # Check for unresponsive alert after failed action
                if self.handle_unresponsive_alert():
                    logger.info("Handled unresponsive alert during recovery")
                    retry_count += 1
                    continue

                logger.info("Executing recovery step 1: KEYCODE_BACK")
                self.device.press("back")
                time.sleep(1)

                logger.info("Executing recovery step 2: Click miniplayer container")
                miniplayer = self.device.xpath(
                    '//*[@resource-id="com.apple.android.music:id/miniplayer_shareplay_container"]'
                )
                if miniplayer.exists:
                    miniplayer.click()
                    time.sleep(1)
                else:
                    logger.error("Miniplayer container not found during recovery")
                    break

            except Exception as e:
                logger.error(f"Error during recovery steps: {e}")
                break

            retry_count += 1

        logger.error(f"Action {func.__name__} failed after {retry_count} recovery attempts")
        return False

    return wrapper


class AppleMusicController(BaseController):
    """Controller for Apple Music automation with error recovery."""

    def __init__(self, device: u2.Device):
        """Initialize Apple Music controller."""
        super().__init__(device)
        self.package_name = AppleMusicConfig.PACKAGE_NAME
        self.app_name = AppleMusicConfig.APP_NAME
        self.isoclipboard_package = "com.example.isolatedclipboard"

        # Set up screen settings during initialization
        if not self.setup_screen_settings():
            logger.warning("Failed to set up screen settings during initialization")

    def check_internet_connection(self, max_retries: int = 5, delay: int = 2) -> bool:
        """Check internet connection using netstat to verify active TCP connections."""
        for attempt in range(max_retries):
            try:
                # Get all TCP connections (both IPv4 and IPv6-mapped IPv4)
                netstat_check = self.device.shell('netstat -n | grep ESTABLISHED | grep -E "^tcp6.*::ffff:|^tcp[^6]"')

                # First check exit code
                if getattr(netstat_check, 'exit_code', 0) != 0:
                    logger.warning(
                        f"Failed to get TCP connections (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {delay}s...")
                    time.sleep(delay)
                    continue

                # Get actual output content
                output = str(getattr(netstat_check, 'output', netstat_check)).strip()
                if not output:  # Check if output is empty
                    logger.warning(
                        f"No TCP connections found (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {delay}s...")
                    time.sleep(delay)
                    continue

                connections = output.split('\n')
                logger.info(f"Found {len(connections)} TCP connections")
                logger.info(f"Sample connection: {connections[0] if connections else 'None'}")
                return True

            except Exception as e:
                logger.error(f"Error checking internet connection: {e}")
                time.sleep(delay)

        logger.error("Failed to establish internet connection after retries.")
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
            logger.error(f"Failed to manage window state: {e}", exc_info=True)
            return False

    def unlock_screen(self) -> bool:
        """Unlock screen without using power button."""
        try:
            logger.info("Starting screen unlock sequence")

            # Use swipe directly to wake and unlock
            self.device.swipe(540, 1800, 540, 900)
            time.sleep(0.5)  # Short delay to verify

            # Verify unlock was successful
            if self.device(resourceId="android:id/statusBarBackground").exists:
                logger.info("Screen unlocked successfully")
                return True

            # If first attempt failed, try using KEYCODE_WAKEUP instead of power button
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

    def ensure_screen_active(self) -> bool:
        """Ensure device screen is active with immediate unlock attempt."""
        try:
            # Check initial state
            device_info = self.device.info
            screen_state = device_info.get('screenState') if device_info else None

            logger.info(f"Current screen state: {screen_state}")

            # Always try quick wake-and-swipe sequence
            return self.unlock_screen()

        except Exception as e:
            logger.error(f"Error ensuring screen active: {e}")
            return self.unlock_screen()  # Try unlock as fallback

    def prepare_for_action(self) -> bool:
        """Prepare device for performing an action."""
        try:
            # First ensure screen is active
            if not self.ensure_screen_active():
                logger.error("Failed to ensure screen active before action")
                return False

            # Bring app to foreground
            self.manage_window_state(minimize=False)
            time.sleep(1)  # Wait for app to come to foreground

            # Verify app is in foreground
            if not self.is_running():
                logger.error("App not in foreground after preparation")
                return False

            return True

        except Exception as e:
            logger.error(f"Error preparing for action: {e}")
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

    @with_error_recovery
    def play_pause(self) -> bool:
        """Toggle play/pause state with error recovery."""
        try:
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

    @with_error_recovery
    def next_track(self) -> bool:
        """Skip to next track with error recovery."""
        try:
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

    @with_error_recovery
    def previous_track(self) -> bool:
        """Go to previous track with error recovery."""
        try:
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

    @with_error_recovery
    def like_current_song(self) -> bool:
        """Like the currently playing song with error recovery."""
        try:
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
        """Toggle shuffle mode with error recovery."""
        try:
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

            # Click FETCH button
            fetch_button = self.device.xpath('//*[@resource-id="com.example.isolatedclipboard:id/buttonFetchUrl2"]')
            if not fetch_button.exists:
                logger.error("FETCH button not found")
                return False

            fetch_button.click()
            logger.info("Clicked FETCH button")
            time.sleep(15)

            # Click shuffle button
            shuffle_button = self.device.xpath('//*[@resource-id="com.apple.android.music:id/button_shuffle"]')
            if not shuffle_button.exists:
                logger.error("Shuffle button not found")
                return False

            shuffle_button.click()
            logger.info("Clicked shuffle button")
            time.sleep(3)

            miniplayer = self.device.xpath(
                '//*[@resource-id="com.apple.android.music:id/miniplayer_shareplay_container"]')
            if not miniplayer.exists:
                miniplayer = self.device.xpath('//*[@resource-id="com.apple.android.music:id/mini_player"]')
                if not miniplayer.exists:
                    miniplayer = self.device.xpath('//*[contains(@resource-id, "miniplayer")]')
                    if not miniplayer.exists:
                        logger.error("Miniplayer not found after trying multiple selectors")
                        return False


            miniplayer.click()
            logger.info("Clicked miniplayer")
            time.sleep(1)
            return True

        except Exception as e:
            logger.error(f"Error with IsoClipboard: {e}")
            return False