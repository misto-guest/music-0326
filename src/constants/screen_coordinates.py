# src/constants/screen_coordinates.py

from typing import Dict, Tuple


class Coordinates:
    """Base class for screen coordinates."""

    def __init__(self, width: int = 1080, height: int = 2400):
        """Initialize with screen dimensions."""
        self.width = width
        self.height = height

    def get_coordinates(self, x_ratio: float, y_ratio: float) -> Tuple[int, int]:
        """Convert ratio coordinates to actual screen coordinates."""
        return (int(x_ratio * self.width), int(y_ratio * self.height))


class AppleMusicCoordinates(Coordinates):
    """Screen coordinates for Apple Music UI elements."""

    # Main controls
    PLAY_PAUSE = (0.5, 0.9)
    NEXT_TRACK = (0.85, 0.9)
    PREV_TRACK = (0.15, 0.9)
    LIKE_BUTTON = (0.121, 0.659)

    # IsoClipboard integration
    ISOCLIPBOARD_LINK = (0.71, 0.731)

    def get_all_coordinates(self) -> Dict[str, Tuple[int, int]]:
        """Get all coordinates as actual screen positions."""
        return {
            'play_pause': self.get_coordinates(*self.PLAY_PAUSE),
            'next_track': self.get_coordinates(*self.NEXT_TRACK),
            'prev_track': self.get_coordinates(*self.PREV_TRACK),
            'like_button': self.get_coordinates(*self.LIKE_BUTTON),
            'isoclipboard': self.get_coordinates(*self.ISOCLIPBOARD_LINK)
        }


class YouTubeMusicCoordinates(Coordinates):
    """Screen coordinates for YouTube Music UI elements."""

    # Main controls
    PLAY_PAUSE = (0.5, 0.9)
    NEXT_TRACK = (0.85, 0.9)
    PREV_TRACK = (0.15, 0.9)

    # Menu and shuffle controls
    MENU_BUTTON = (0.837, 0.456)
    SHUFFLE_BUTTON = (0.252, 0.621)

    # IsoClipboard integration
    ISOCLIPBOARD_LINK = (0.71, 0.954)

    def get_all_coordinates(self) -> Dict[str, Tuple[int, int]]:
        """Get all coordinates as actual screen positions."""
        return {
            'play_pause': self.get_coordinates(*self.PLAY_PAUSE),
            'next_track': self.get_coordinates(*self.NEXT_TRACK),
            'prev_track': self.get_coordinates(*self.PREV_TRACK),
            'menu_button': self.get_coordinates(*self.MENU_BUTTON),
            'shuffle_button': self.get_coordinates(*self.SHUFFLE_BUTTON),
            'isoclipboard': self.get_coordinates(*self.ISOCLIPBOARD_LINK)
        }