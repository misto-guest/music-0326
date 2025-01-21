import time
from typing import Optional, Callable
import uiautomator2 as u2
from functools import wraps
from src.controllers.base_controller import BaseController
from src.constants.app_configs import AppleMusicConfig
from src.utils.logging_utils import setup_logger

logger = setup_logger(__name__)


def with_error_recovery(func: Callable) -> Callable:
    """Decorator to add error recovery for Apple Music actions."""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        max_retries = 2
        retry_count = 0

        while retry_count <= max_retries:
            result = func(self, *args, **kwargs)
            if result:
                return True

            logger.warning(f"Apple Music action {func.__name__} failed, attempt {retry_count + 1}")

            try:
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

    def ensure_screen_active(self) -> bool:
        """Ensure device screen is active and ready for interactions."""
        try:
            # First try to get basic device info
            device_info = self.device.info
            if not device_info:
                logger.warning("Could not get device info, attempting basic screen wake")
                # Try basic screen wake sequence
                self.device.screen_on()
                time.sleep(1)
                self.device.press('power')
                time.sleep(1)
                self.device.swipe(540, 1800, 540, 900)
                time.sleep(1)
                return True

            # Get screen state if available
            screen_state = device_info.get('screenState')

            # If we can't determine screen state, try basic wake sequence
            if screen_state is None:
                logger.warning("Screen state unknown, attempting basic screen wake")
                self.device.screen_on()
                time.sleep(1)
                return True

            logger.info(f"Current screen state: {screen_state}")

            # If screen is off (2) or doze (3), wake it up
            if screen_state in [2, 3]:
                logger.info("Screen is off or in doze mode, waking up")
                self.device.screen_on()
                time.sleep(1)

                # Verify wake up succeeded
                new_state = self.device.info.get('screenState')
                if new_state in [2, 3]:
                    logger.warning("First wake attempt failed, trying alternate method")
                    # Try alternate wake method
                    self.device.press('power')
                    time.sleep(1)
                    return True

            # If screen is locked (1), unlock it
            if screen_state == 1:
                logger.info("Screen is locked, unlocking")
                # Press power to wake
                self.device.press('power')
                time.sleep(1)
                # Swipe up to unlock
                self.device.swipe(540, 1800, 540, 900)
                time.sleep(1)

            # Verify screen is in a usable state
            final_state = self.device.info.get('screenState')
            if final_state not in [0, 1, None]:  # Include None as acceptable since we've tried wake sequence
                logger.error(f"Failed to activate screen, final state: {final_state}")
                return False

            logger.info("Screen is active and ready")
            return True

        except Exception as e:
            logger.error(f"Error ensuring screen active: {e}")
            # Try basic wake sequence as fallback
            try:
                self.device.screen_on()
                time.sleep(1)
                return True
            except:
                return False

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
                logger.error("Miniplayer not found")
                return False

            miniplayer.click()
            logger.info("Clicked miniplayer")
            time.sleep(1)
            return True

        except Exception as e:
            logger.error(f"Error with IsoClipboard: {e}")
            return False