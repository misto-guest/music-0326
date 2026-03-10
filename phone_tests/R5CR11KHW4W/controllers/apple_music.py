# Standalone Apple Music Controller for Phone R5CR11KHW4W
# DO NOT MODIFY PRODUCTION CODE - This is a test copy
# Version: test-v1.0 | Created: 2026-03-04
# Purpose: Test improved shuffle button detection

import re
import time
import logging
from typing import Dict
import uiautomator2 as u2

logger = logging.getLogger(__name__)


class AppleMusicController:
    """Controller for Apple Music automation - TEST VERSION for R5CR11KHW4W."""

    def __init__(self, device: u2.Device):
        self.device = device
        self.package_name = "com.apple.android.music"
        self.isoclipboard_package = "com.example.isolatedclipboard"
        self.initial_rotation_state = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Save initial rotation
        self.initial_rotation_state = self.get_rotation_settings()
        
        # Setup screen
        self.setup_screen_settings()

    def get_rotation_settings(self) -> Dict[str, str]:
        try:
            auto_rotate = self.device.shell('settings get system accelerometer_rotation').output.strip()
            user_rotation = self.device.shell('settings get system user_rotation').output.strip()
            return {'auto_rotate': auto_rotate, 'user_rotation': user_rotation}
        except Exception as e:
            logger.error(f"Error getting rotation settings: {e}")
            return {}

    def _force_disable_rotation(self) -> bool:
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

    def _restore_rotation_state(self, initial_state: dict) -> None:
        try:
            if 'auto_rotate' in initial_state:
                self.device.shell(f'settings put system accelerometer_rotation {initial_state["auto_rotate"]}')
            if 'user_rotation' in initial_state:
                self.device.shell(f'settings put system user_rotation {initial_state["user_rotation"]}')
            logger.info("Restored initial rotation state")
        except Exception as e:
            logger.error(f"Error restoring rotation state: {e}")

    def setup_screen_settings(self) -> bool:
        try:
            logger.info("Setting up screen settings")
            self.device.shell('settings put system screen_off_timeout 1800000')
            self.device.shell('settings put global stay_on_while_plugged_in 3')
            timeout = self.device.shell('settings get system screen_off_timeout')
            if '1800000' in str(timeout):
                logger.info("Screen settings configured successfully")
                return True
            return False
        except Exception as e:
            logger.error(f"Error setting up screen settings: {e}")
            return False

    def unlock_screen(self) -> bool:
        try:
            logger.info("Ensuring screen is on")
            self.device.shell('input keyevent KEYCODE_WAKEUP')
            time.sleep(1)
            self.device.press('home')
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Error unlocking screen: {e}")
            return False

    def is_running(self) -> bool:
        try:
            if self.device(packageName=self.package_name).exists:
                return True
            recents = self.device.shell("dumpsys activity recents | grep -i '.amcKGERRbgaxjBBPED'")
            return recents and ".amcKGERRbgaxjBBPED" in str(recents)
        except Exception as e:
            logger.error(f"Error checking if Apple Music running: {e}")
            return False

    def start_app(self) -> bool:
        try:
            logger.info("Starting Apple Music")
            command = "monkey -p com.apple.android.music -c android.intent.category.LAUNCHER 1"
            self.device.shell(command)
            time.sleep(3)
            return self.is_running()
        except Exception as e:
            logger.error(f"Error starting Apple Music: {e}")
            return False

    def prepare_for_action(self) -> bool:
        try:
            self.unlock_screen()
            
            current_app = self.device.app_current()
            current_package = current_app.get("package", "")
            logger.info(f"Current package: {current_package}")

            if "com.apple.android.music" not in current_package and ".amcKGERRbgaxjBBPED" not in current_package:
                logger.info("Apple Music not in foreground, launching...")
                self.start_app()
                time.sleep(2)
            
            return True
        except Exception as e:
            logger.error(f"Error preparing for action: {e}")
            return False

    def check_play_state(self) -> bool:
        """Check if Apple Music is currently playing."""
        try:
            time.sleep(2)
            result = self.device.shell("dumpsys media_session")
            raw_output = getattr(result, 'output', result)
            
            if "state=PLAYING(3)" in raw_output or "state=3" in raw_output:
                logger.info("Apple Music is PLAYING")
                return True
            
            # Check for Apple Music session
            if "MediaPlaybackService com.apple.android.music" in raw_output:
                # Parse state
                pattern = re.compile(r"PlaybackState\s*\{state=(?:[A-Z]+)?\(?(\d+)\)?")
                for line in raw_output.split("\n"):
                    if "state=PlaybackState" in line:
                        match = pattern.search(line)
                        if match:
                            state = int(match.group(1))
                            return state == 3
            
            return False
        except Exception as e:
            logger.error(f"Error checking play state: {e}")
            return False

    def get_current_song(self) -> dict:
        """Get current song info from media_session."""
        try:
            result = self.device.shell("dumpsys media_session")
            raw_output = getattr(result, 'output', result)
            
            # Find metadata line
            for line in raw_output.split("\n"):
                if "metadata:" in line and "description=" in line:
                    # Parse: metadata: size=51, description=Title, Artist, Album
                    parts = line.split("description=")
                    if len(parts) > 1:
                        desc = parts[1].strip()
                        items = [x.strip() for x in desc.split(",")]
                        if len(items) >= 2:
                            return {
                                "title": items[0] if items else "Unknown",
                                "artist": items[1] if len(items) > 1 else "Unknown",
                                "album": items[2] if len(items) > 2 else "Unknown"
                            }
            return {}
        except Exception as e:
            logger.error(f"Error getting current song: {e}")
            return {}

    def check_login_status(self) -> tuple:
        """Check if Apple Music is logged in. Returns (is_logged_in, info)."""
        try:
            # Navigate to library
            library = self.device.xpath('//*[@content-desc="Library"]')
            if library.exists:
                library.click()
                time.sleep(2)
                
                # Check for songs list
                songs = self.device.xpath('//*[@text="Songs"]')
                if songs.exists:
                    logger.info("LOGIN OK - Library accessible")
                    return True, "Library accessible"
            
            # Check for sign-in prompt
            sign_in = self.device.xpath('//*[contains(@text, "Sign In") or contains(@text, "Log In")]')
            if sign_in.exists:
                logger.warning("NOT LOGGED IN - Sign In button found")
                return False, "Sign In required"
            
            return None, "Could not determine"
        except Exception as e:
            logger.error(f"Error checking login: {e}")
            return None, str(e)

    def navigate_to_library_songs(self) -> bool:
        """Navigate to Library > Songs."""
        try:
            logger.info("Navigating to Library > Songs")
            
            # Click Library tab
            library = self.device.xpath('//*[@content-desc="Library"]')
            if library.exists:
                library.click()
                time.sleep(2)
            
            # Click Songs
            songs = self.device.xpath('//*[@text="Songs"]')
            if songs.exists:
                songs.click()
                time.sleep(2)
                logger.info("Successfully navigated to Songs")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error navigating: {e}")
            return False

    def _start_isoclipboard(self) -> bool:
        """Start IsoClipboard app."""
        try:
            logger.info("Starting IsoClipboard")
            self._force_disable_rotation()
            
            self.device.app_stop(self.isoclipboard_package)
            time.sleep(1)
            
            self.device.shell(f'am start -W {self.isoclipboard_package}/.MainActivity --activity-single-top')
            time.sleep(3)
            
            # Verify
            current = self.device.app_current()
            if current.get('package') == self.isoclipboard_package:
                logger.info("IsoClipboard started successfully")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error starting IsoClipboard: {e}")
            return False

    def _click_fetch_button(self) -> bool:
        """Click FETCH button in IsoClipboard."""
        try:
            # Try multiple FETCH buttons
            fetch_selectors = [
                '//*[@resource-id="com.example.isolatedclipboard:id/buttonFetchUrl2"]',
                '//*[@resource-id="com.example.isolatedclipboard:id/buttonFetchUrl1"]',
                '//*[@text="FETCH"]',
            ]
            
            for selector in fetch_selectors:
                btn = self.device.xpath(selector)
                if btn.exists:
                    btn.click()
                    logger.info(f"Clicked FETCH button")
                    time.sleep(15)  # Wait for content load
                    return True
            
            logger.error("FETCH button not found")
            return False
        except Exception as e:
            logger.error(f"Error clicking FETCH: {e}")
            return False

    def _check_internet(self) -> bool:
        """Check for TCP connections."""
        try:
            result = self.device.shell('netstat -n | grep ESTABLISHED')
            output = str(getattr(result, 'output', result)).strip()
            if output:
                lines = output.split('\n')
                logger.info(f"Found {len(lines)} TCP connections")
                return len(lines) > 0
            return False
        except Exception as e:
            logger.error(f"Error checking internet: {e}")
            return False

    def _click_shuffle_button(self) -> bool:
        """Click shuffle button - IMPROVED VERSION with multiple strategies."""
        try:
            logger.info("Looking for shuffle button...")
            
            # Strategy 1: content-desc="play shuffled" (Library view shuffle)
            shuffle = self.device.xpath('//*[@content-desc="play shuffled"]')
            if shuffle.exists:
                shuffle.click()
                logger.info("Clicked 'play shuffled' button")
                return True
            
            # Strategy 2: content-desc="Shuffle On" or "Shuffle Off" (player control)
            shuffle = self.device.xpath('//*[@content-desc="Shuffle On" or @content-desc="Shuffle Off"]')
            if shuffle.exists:
                shuffle.click()
                logger.info("Clicked player shuffle toggle")
                return True
            
            # Strategy 3: resource-id + LinearLayout (Library button)
            shuffle = self.device.xpath('//*[@resource-id="com.apple.android.music:id/button_shuffle" and contains(@class, "LinearLayout")]')
            if shuffle.exists:
                shuffle.click()
                logger.info("Clicked shuffle via resource-id + LinearLayout")
                return True
            
            # Strategy 4: text="Shuffle"
            shuffle = self.device.xpath('//*[@text="Shuffle"]')
            if shuffle.exists:
                shuffle.click()
                logger.info("Clicked shuffle via text")
                return True
            
            # Strategy 5: KeyEvent fallback
            logger.warning("Shuffle button not found, using keyevent fallback")
            self.device.shell('input keyevent KEYCODE_MEDIA_PLAY')
            time.sleep(2)
            return True
            
        except Exception as e:
            logger.error(f"Error clicking shuffle: {e}")
            # Last resort fallback
            self.device.shell('input keyevent KEYCODE_MEDIA_PLAY')
            return True

    def handle_isoclipboard(self) -> bool:
        """Main IsoClipboard + Shuffle workflow."""
        try:
            # Disable rotation
            if not self._force_disable_rotation():
                logger.warning("Could not disable rotation, continuing...")
            
            # Start IsoClipboard
            if not self._start_isoclipboard():
                logger.error("Failed to start IsoClipboard")
                return False
            
            # Click FETCH
            if not self._click_fetch_button():
                logger.error("Failed to click FETCH")
                return False
            
            # Check internet
            if not self._check_internet():
                logger.warning("No internet connection detected")
            
            # Return to Apple Music
            self.start_app()
            time.sleep(2)
            
            # Navigate to Library > Songs
            self.navigate_to_library_songs()
            
            # Click shuffle
            if not self._click_shuffle_button():
                logger.error("Failed to click shuffle")
                return False
            
            time.sleep(3)
            
            # Verify playback
            if self.check_play_state():
                logger.info("SUCCESS: Apple Music is now playing!")
                song = self.get_current_song()
                if song:
                    logger.info(f"Now playing: {song.get('title')} - {song.get('artist')}")
                return True
            else:
                logger.warning("Music not playing yet, sending play command")
                self.device.shell('input keyevent KEYCODE_MEDIA_PLAY')
                time.sleep(3)
                return self.check_play_state()
            
        except Exception as e:
            logger.error(f"Error in handle_isoclipboard: {e}")
            return False
        finally:
            # Restore rotation
            if self.initial_rotation_state:
                self._restore_rotation_state(self.initial_rotation_state)

    def cleanup(self):
        """Cleanup."""
        try:
            if self.initial_rotation_state:
                self._restore_rotation_state(self.initial_rotation_state)
            logger.info("Cleanup complete")
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")
