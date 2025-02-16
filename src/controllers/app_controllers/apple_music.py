# src/controllers/app_controllers/apple_music.py

import re
import time
from typing import Dict
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

    def check_play_state(self) -> bool:
        """
        Check if Apple Music is currently playing by parsing `dumpsys media_session`.
        Returns True if state=PLAYING(3), else False.
        """
        try:
            time.sleep(2)

            cmd = "dumpsys media_session"
            result = self.device.shell(cmd)
            raw_output = getattr(result, 'output', result)

            if not raw_output:
                logger.error("No output from dumpsys media_session.")
                return False

            lines = raw_output.split("\n")

            apple_music_session = []
            capturing = False

            for line in lines:
                if "MediaPlaybackService com.apple.android.music" in line:
                    capturing = True
                if capturing:
                    apple_music_session.append(line)
                    if line.strip() == "":
                        break

            if not apple_music_session:
                logger.info("No active Apple Music session found in media_session.")
                return False

            # Search for state=PlaybackState {state=PAUSED(2), ...} or PLAYING(3)
            pattern = re.compile(r"PlaybackState\s*\{state=(?:[A-Z]+)?\(?(\d+)\)?")
            for line in apple_music_session:
                if "state=PlaybackState" in line:
                    match = pattern.search(line)
                    if match:
                        numeric_state = int(match.group(1))  # 2 (paused) or 3 (playing)
                        is_playing = (numeric_state == 3)
                        logger.info(f"Apple Music session state={numeric_state}, is_playing={is_playing}")
                        return is_playing

            logger.info("PlaybackState not found or not recognized (not playing).")
            return False

        except Exception as e:
            logger.error(f"Error checking Apple Music play state: {e}")
            return False

    def ensure_playing(self) -> bool:
        """
        Ensure Apple Music is playing by checking playback state
        and sending a media keyevent if needed.
        """
        try:
            if not self.prepare_for_action():
                logger.error("Could not prepare for play state check.")
                return False

            if not self.check_play_state():
                logger.info("Music is NOT playing, sending play command...")
                self.device.shell('input keyevent KEYCODE_MEDIA_PLAY_PAUSE')

                time.sleep(5)

                if not self.check_play_state():
                    logger.error("Failed to start playback (still not playing).")
                    return False

                logger.info("Successfully started playback.")
            else:
                logger.info("Music is already playing.")

            return True

        except Exception as e:
            logger.error(f"Error ensuring playing state: {e}")
            return False

    def prepare_app_and_play(self) -> bool:
        """Consolidated method to prepare app and ensure it's playing."""
        try:
            if not self.prepare_for_action():
                logger.error("Could not prepare app for action")
                return False

            # Now check play state and handle if needed
            if not self.check_play_state():
                logger.info("Music is not playing, sending play command")
                self.device.shell('input keyevent KEYCODE_MEDIA_PLAY_PAUSE')
                time.sleep(7)  # Wait for play state to update

                # Final check
                return self.check_play_state()

            return True
        except Exception as e:
            logger.error(f"Error in prepare_app_and_play: {e}")
            return False

    def setup_screen_settings(self) -> bool:
        try:
            logger.info("Setting up screen settings")
            self.device.shell('settings put system screen_off_timeout 1800000')
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
        try:
            logger.info("Ensuring screen is on (no swipes).")

            # Send KEYCODE_WAKEUP to turn screen on
            self.device.shell('input keyevent KEYCODE_WAKEUP')
            time.sleep(1)

            # Press HOME to exit any lock screen if there's no secure lock
            self.device.press('home')
            time.sleep(1)

            if self.device(clickable=True).exists:
                logger.info("Screen is on and has clickable elements.")
                return True

            logger.warning("Screen might still be locked or unresponsive, continuing anyway.")
            return True
        except Exception as e:
            logger.error(f"Error during simplified screen unlock: {e}")
            return False

    def ensure_screen_active(self) -> bool:
        try:
            device_info = self.device.info
            screen_state = device_info.get('screenState') if device_info else None
            logger.info(f"Current screen state: {screen_state}")

            return self.unlock_screen()
        except Exception as e:
            logger.error(f"Error ensuring screen active: {e}")
            return self.unlock_screen()

    def check_internet_connection(self, max_retries: int = 5, delay: int = 2) -> bool:
        """Check internet connection using netstat."""
        for attempt in range(max_retries):
            try:
                netstat_check = self.device.shell(
                    'netstat -n | grep ESTABLISHED | grep -E "^tcp6.*::ffff:|^tcp[^6]"'
                )
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
        try:
            if not self.ensure_screen_active():
                logger.error("Failed to ensure screen is active before action.")
                return False

            current_app_info = self.device.app_current()
            current_package = current_app_info.get("package", "")
            logger.info(f"Current active package: {current_package}")

            # Force stop IsoClipboard if it's in foreground
            if current_package == self.isoclipboard_package:
                logger.info("Force stopping IsoClipboard")
                self.device.app_stop(self.isoclipboard_package)
                time.sleep(2)

            def is_apple_music_active(text: str) -> bool:
                return ("com.apple.android.music" in text) or (".amcKGERRbgaxjBBPED" in text)

            if not is_apple_music_active(current_package):
                logger.info("Apple Music not detected in foreground via app_current(). Checking recents...")
                recents_response = self.device.shell(
                    "dumpsys activity recents | grep 'Recent #' | grep -i '.amcKGERRbgaxjBBPED'")
                recents_output = recents_response.output if hasattr(recents_response, "output") else recents_response
                logger.info(f"Recents output: {recents_output.strip()}")

                # Press HOME first to ensure clean state
                logger.info("Pressing HOME key to ensure clean state")
                self.device.press('home')
                time.sleep(1)

                if not is_apple_music_active(recents_output):
                    logger.info("Apple Music not running according to recents. Starting it normally.")
                    # Try am start first
                    try:
                        start_command = f'am start -n {self.package_name}/com.apple.android.music.activities.MainActivity'
                        logger.info(f"Executing am start command: {start_command}")
                        self.device.shell(start_command)
                        time.sleep(3)
                    except Exception as e:
                        logger.error(f"am start failed: {e}")
                        return self.start_app()
                else:
                    logger.info("Apple Music found in recents. Trying multiple launch methods.")

                    # Try monkey command first
                    command = "monkey -p com.apple.android.music -c android.intent.category.LAUNCHER 1"
                    logger.info(f"Executing monkey command: {command}")
                    result = self.device.shell(command)
                    logger.info(f"Monkey command result: {result}")
                    time.sleep(3)

                    # Check if monkey command worked
                    current_app_info = self.device.app_current()
                    current_package = current_app_info.get("package", "")

                    if not is_apple_music_active(current_package):
                        logger.info("Monkey command failed, trying am start...")
                        try:
                            start_command = f'am start -n {self.package_name}/com.apple.android.music.activities.MainActivity'
                            logger.info(f"Executing am start command: {start_command}")
                            self.device.shell(start_command)
                            time.sleep(3)
                        except Exception as e:
                            logger.error(f"am start failed: {e}")
                            return self.start_app()

                # Final check
                current_app_info = self.device.app_current()
                current_package = current_app_info.get("package", "")
                logger.info(f"Final check - current active package: {current_package}")

                if not is_apple_music_active(current_package):
                    logger.error("All attempts to bring Apple Music to foreground failed.")
                    # One last attempt using app_start
                    return self.start_app()
                else:
                    logger.info("Apple Music has been successfully brought to the foreground.")
            else:
                logger.info("Apple Music is already in the foreground.")

            # Wait for UI to settle
            time.sleep(2)
            return True

        except Exception as e:
            logger.error(f"Error preparing for action: {e}")
            return False

    def manage_window_state(self, minimize: bool = True) -> bool:
        try:
            if minimize:
                self.device.press('home')
                time.sleep(1)
                return True
            else:
                if self.is_running():
                    command = (
                        "monkey -p com.apple.android.music -c android.intent.category.LAUNCHER 1"
                    )
                    self.device.shell(command)
                    time.sleep(3)
                    return True
                else:
                    return self.start_app()
        except Exception as e:
            logger.error(f"Failed to manage window state: {e}")
            return False

    def start_app(self) -> bool:
        try:
            logger.info("Starting Apple Music via app_start()")
            self.device.app_start(self.package_name)
            time.sleep(2)

            if self.is_running():
                logger.info("Apple Music is now in the foreground")
                return True
            else:
                logger.error("Apple Music did not appear in foreground after start attempt")
                return False
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
        try:
            # Check if any UI element with the Apple Music package exists.
            if self.device(packageName=self.package_name).exists:
                return True

            # Optionally, check the recents output for the internal alias.
            recents = self.device.shell("dumpsys activity recents | grep -i '.amcKGERRbgaxjBBPED'")
            if recents and ".amcKGERRbgaxjBBPED" in recents.output:
                return True

            return False
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
        try:
            logger.info("Attempting play/pause...")
            if not self.prepare_for_action():
                logger.info("Using keyevent fallback for play/pause")
                self.device.shell('input keyevent KEYCODE_MEDIA_PLAY_PAUSE')
                return True

            self.device.shell('input keyevent KEYCODE_MEDIA_PLAY_PAUSE')
            time.sleep(1)
            self._ensure_mini_player()
            return True
        except Exception as e:
            logger.error(f"Error toggling play/pause: {e}")
            self._ensure_mini_player()
            return False

    def next_track(self) -> bool:
        try:
            logger.info("Attempting next track...")

            if not self.prepare_app_and_play():
                logger.info("Preparation failed, using keyevent fallback for next track")
                self.device.shell('input keyevent KEYCODE_MEDIA_NEXT')
                time.sleep(2)
                self._ensure_mini_player()
                return True

            time.sleep(2)
            next_button = self.device.xpath('//*[@resource-id="com.apple.android.music:id/next_fast_forward"]')

            if self._is_element_clickable(next_button):
                next_button.click()
                logger.info("Clicked next track button")
            else:
                logger.info("Next button not clickable, using keyevent fallback")
                self.device.shell('input keyevent KEYCODE_MEDIA_NEXT')

            time.sleep(2)
            self._ensure_mini_player()
            return True

        except Exception as e:
            logger.error(f"Error skipping to next track: {e}")
            try:
                self.device.shell('input keyevent KEYCODE_MEDIA_NEXT')
                time.sleep(2)
                self._ensure_mini_player()
                return True
            except:
                self._ensure_mini_player()
                return False

    def previous_track(self) -> bool:
        try:
            logger.info("Attempting previous track...")

            if not self.prepare_app_and_play():
                logger.info("Preparation failed, using keyevent fallback for previous track")
                self.device.shell('input keyevent KEYCODE_MEDIA_PREVIOUS')
                time.sleep(2)
                self._ensure_mini_player()
                return True

            time.sleep(2)
            prev_button = self.device.xpath('//*[@resource-id="com.apple.android.music:id/previous_rewind"]')

            if self._is_element_clickable(prev_button):
                prev_button.click()
                logger.info("Clicked previous track button")
            else:
                logger.info("Previous button not clickable, using keyevent fallback")
                self.device.shell('input keyevent KEYCODE_MEDIA_PREVIOUS')

            time.sleep(2)
            self._ensure_mini_player()
            return True

        except Exception as e:
            logger.error(f"Error going to previous track: {e}")
            try:
                self.device.shell('input keyevent KEYCODE_MEDIA_PREVIOUS')
                time.sleep(2)
                self._ensure_mini_player()
                return True
            except:
                self._ensure_mini_player()
                return False

    def like_current_song(self) -> bool:
        try:
            logger.info("Starting like song action...")

            if not self.prepare_app_and_play():
                logger.error("Cannot like song, app preparation failed")
                self._ensure_mini_player()
                return False

            like_button = self.device.xpath('//*[@resource-id="com.apple.android.music:id/list_favorite_icon"]')

            if not self._is_element_clickable(like_button):
                logger.error("Like button not clickable")
                self._ensure_mini_player()
                return False

            like_button.click()
            logger.info("Clicked like button")
            time.sleep(2)
            self._ensure_mini_player()
            return True
        except Exception as e:
            logger.error(f"Error liking current song: {e}")
            self._ensure_mini_player()
            return False

    def get_rotation_settings(self) -> Dict[str, str]:
        """Get current rotation settings."""
        try:
            auto_rotate = self.device.shell('settings get system accelerometer_rotation').output.strip()
            user_rotation = self.device.shell('settings get system user_rotation').output.strip()
            return {
                'auto_rotate': auto_rotate,
                'user_rotation': user_rotation
            }
        except Exception as e:
            logger.error(f"Error getting rotation settings: {e}")
            return {}

    def _force_disable_rotation(self) -> bool:
        """Force disable rotation with verification."""
        try:
            for _ in range(3):
                self.device.shell('settings put system accelerometer_rotation 0')
                time.sleep(0.5)
                current = self.device.shell('settings get system accelerometer_rotation').output.strip()
                if current == '0':
                    logger.info("Successfully disabled rotation")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error forcing rotation disable: {e}")
            return False

    def _verify_rotation_disabled(self) -> bool:
        """Verify rotation is disabled and fix if needed."""
        try:
            current = self.device.shell('settings get system accelerometer_rotation').output.strip()
            if current != '0':
                logger.warning("Rotation got enabled, forcing disable")
                return self._force_disable_rotation()
            return True
        except Exception as e:
            logger.error(f"Error verifying rotation: {e}")
            return False

    def _restore_rotation_state(self, initial_state: dict) -> None:
        """Restore rotation to initial state."""
        try:
            if 'auto_rotate' in initial_state:
                self.device.shell(f'settings put system accelerometer_rotation {initial_state["auto_rotate"]}')
            if 'user_rotation' in initial_state:
                self.device.shell(f'settings put system user_rotation {initial_state["user_rotation"]}')
            logger.info("Restored initial rotation state")
        except Exception as e:
            logger.error(f"Error restoring rotation state: {e}")

    def handle_isoclipboard(self) -> bool:
        initial_rotation_state = None
        try:
            initial_rotation_state = self.get_rotation_settings()
            logger.info(f"Initial rotation settings: {initial_rotation_state}")

            # Force disable rotation
            if not self._force_disable_rotation():
                logger.error("Failed to disable rotation")
                return False

            # Start IsoClipboard
            if not self._start_isoclipboard_safely():
                if self.needs_restart("IsoClipboard"):
                    logger.info("Retrying IsoClipboard after force-close")
                    self.clear_restart_flag("IsoClipboard")
                    time.sleep(2)
                    if not self._start_isoclipboard_safely():
                        return False
                else:
                    return False

            # Click FETCH
            if not self._handle_fetch_operation():
                return False

            # Check if Apple Music was closed
            if self.needs_restart("Apple Music"):
                logger.info("Restarting Apple Music after force-close")
                self.clear_restart_flag("Apple Music")
                time.sleep(2)
                if not self.prepare_for_action():
                    return False

            # Shuffle + miniplayer
            if not self._handle_shuffle_and_miniplayer():
                return False

            return True
        except Exception as e:
            logger.error(f"Error with IsoClipboard: {e}")
            return False
        finally:
            # Restore rotation
            if initial_rotation_state:
                self._restore_rotation_state(initial_rotation_state)

    def _start_isoclipboard_safely(self) -> bool:
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logger.info(f"Starting IsoClipboard attempt {attempt + 1}/{max_attempts}")

                if not self._verify_rotation_disabled():
                    logger.error("Rotation control lost before app start")
                    continue

                self.device.app_stop(self.isoclipboard_package)
                time.sleep(1)
                self.device.shell(
                    f'am start -W {self.isoclipboard_package}/.MainActivity --activity-single-top'
                )
                time.sleep(3)

                if not self._verify_rotation_disabled():
                    logger.error("Rotation got enabled during app start")
                    continue

                for _ in range(3):
                    current_app = self.device.app_current()
                    if current_app.get('package') == self.isoclipboard_package:
                        logger.info("IsoClipboard successfully brought to foreground")
                        return True
                    logger.warning("IsoClipboard not in foreground, retrying...")
                    self.device.press("home")
                    time.sleep(1)
                    self.device.shell(
                        f'am start -W {self.isoclipboard_package}/.MainActivity --activity-single-top'
                    )
                    time.sleep(2)

                logger.error(f"Failed to bring IsoClipboard to foreground on attempt {attempt + 1}")

            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}: {e}")

            time.sleep(2)

        logger.error("All attempts to start IsoClipboard safely failed")
        return False

    def _handle_fetch_operation(self) -> bool:
        try:
            if not self._verify_rotation_disabled():
                return False

            fetch_button = self.device.xpath(
                '//*[@resource-id="com.example.isolatedclipboard:id/buttonFetchUrl2"]'
            )
            if not fetch_button.exists:
                logger.error("FETCH button not found")
                return False

            fetch_button.click()
            logger.info("Clicked FETCH button")
            time.sleep(15)

            if not self.check_internet_connection():
                logger.error("No internet connection available")
                return False

            return True
        except Exception as e:
            logger.error(f"Error in fetch operation: {e}")
            return False

    def _handle_shuffle_and_miniplayer(self) -> bool:
        try:
            if not self._verify_rotation_disabled():
                return False

            shuffle_button = self.device.xpath(
                '//*[@resource-id="com.apple.android.music:id/button_shuffle"]'
            )
            if not shuffle_button.exists:
                logger.error("Shuffle button not found")
                return False

            shuffle_button.click()
            logger.info("Clicked shuffle button")
            time.sleep(3)

            miniplayer_selectors = [
                '//*[@resource-id="com.apple.android.music:id/miniplayer_shareplay_container"]',
                '//*[@resource-id="com.apple.android.music:id/mini_player"]',
                '//*[contains(@resource-id, "miniplayer")]'
            ]

            for selector in miniplayer_selectors:
                if not self._verify_rotation_disabled():
                    continue

                mini = self.device.xpath(selector)
                if mini.exists:
                    mini.click()
                    logger.info(f"Clicked miniplayer using selector: {selector}")
                    time.sleep(1)
                    return True

            logger.error("Miniplayer not found after trying multiple selectors")
            return False
        except Exception as e:
            logger.error(f"Error handling shuffle and miniplayer: {e}")
            return False

    def _ensure_mini_player(self):
        try:
            logger.info("Searching for mini_player element...")
            mini_player = self.device.xpath('//*[@resource-id="com.apple.android.music:id/mini_player"]')
            if mini_player.exists:
                mini_player.click()
                logger.info("Clicked mini_player to ensure correct Apple Music state")
                time.sleep(1)
            else:
                logger.info("mini_player element not found")
        except Exception as e:
            logger.error(f"Error ensuring mini_player state: {e}")

    def _is_element_clickable(self, element) -> bool:
        """Check if element exists and is clickable."""
        try:
            return element.exists and element.info.get('clickable', False)
        except Exception as e:
            logger.error(f"Error checking element clickability: {e}")
            return False