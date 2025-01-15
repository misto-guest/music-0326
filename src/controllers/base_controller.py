# src/controllers/base_controller.py

from abc import ABC, abstractmethod
from typing import Optional
import uiautomator2 as u2
from src.utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class BaseController(ABC):
    """Abstract base class for music app controllers."""

    def __init__(self, device: u2.Device):
        """Initialize base controller."""
        self.device = device

    @abstractmethod
    def start_app(self) -> bool:
        """Start the music app."""
        pass

    @abstractmethod
    def stop_app(self) -> bool:
        """Stop the music app."""
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """Check if the app is currently running."""
        pass

    @abstractmethod
    def force_stop(self) -> bool:
        """Force stop the app."""
        pass

    @abstractmethod
    def play_pause(self) -> bool:
        """Toggle play/pause state."""
        pass

    @abstractmethod
    def next_track(self) -> bool:
        """Skip to next track."""
        pass

    @abstractmethod
    def previous_track(self) -> bool:
        """Go to previous track."""
        pass

    @abstractmethod
    def like_current_song(self) -> bool:
        """Like the currently playing song."""
        pass

    @abstractmethod
    def handle_isoclipboard(self) -> bool:
        """Handle IsoClipboard interaction."""
        pass

    def safe_click(self, x: float, y: float, description: str = "") -> bool:
        """Safely perform a click operation with logging."""
        try:
            screen_info = self.device.window_size()
            click_x = int(x * screen_info[0])
            click_y = int(y * screen_info[1])

            logger.debug(f"Clicking {description} at: {click_x}, {click_y}")
            self.device.click(click_x, click_y)
            return True

        except Exception as e:
            logger.error(f"Error clicking {description}: {e}")
            return False

    def wait_for_element(self, timeout: int = 5, **selector_kwargs) -> Optional[u2.UiObject]:
        """Wait for an element to appear with timeout."""
        try:
            element = self.device(**selector_kwargs)
            return element if element.exists(timeout=timeout) else None
        except Exception as e:
            logger.error(f"Error waiting for element: {e}")
            return None