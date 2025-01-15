# src/constants/app_configs.py

from typing import Dict


class MusicApps:
    """Configuration for music apps."""

    REGISTERED_APPS: Dict[str, str] = {
        "com.aspiro.tidal": "Tidal",
        "com.google.android.apps.youtube.music": "YouTube Music",
        "com.beatport.mobile": "Beatport",
        "com.beatport.mobilf": "Beatport (Clone)",
        "com.apple.android.music.clone": "Apple Music (Clone)",
        "com.apple.android.music.clone2": "Apple Music (Clone 2)"
    }

    BASE_PACKAGES: Dict[str, str] = {
        "com.beatport": "Beatport",
        "com.apple.android.music": "Apple Music"
    }


class AppleMusicConfig:
    """Configuration for Apple Music."""

    PACKAGE_NAME = "com.apple.android.music"
    ACTIVITY_NAME = "com.apple.android.music.MainActivity"
    APP_NAME = "Apple Music"

    # UI Element IDs
    PLAY_PAUSE_BUTTON = "playback_controls_play_pause"
    NEXT_TRACK_BUTTON = "playback_controls_next"
    PREV_TRACK_BUTTON = "playback_controls_previous"
    LIKE_BUTTON = "like_button"


class YouTubeMusicConfig:
    """Configuration for YouTube Music."""

    PACKAGE_NAME = "com.google.android.apps.youtube.music"
    ACTIVITY_NAME = "com.google.android.apps.youtube.music.activities.MusicActivity"
    APP_NAME = "YouTube Music"

    # UI Element IDs
    PLAY_PAUSE_BUTTON = "player_control_play_pause_replay_button"
    NEXT_BUTTON = "player_control_next_button"
    PREV_BUTTON = "player_control_previous_button"
    SHUFFLE_BUTTON = "shuffle_button"


class IsoClipboardConfig:
    """Configuration for IsoClipboard app."""

    PACKAGE_NAME = "com.example.isolatedclipboard"
    ACTIVITY_NAME = "com.example.isolatedclipboard.MainActivity"
    FETCH_BUTTON_ID = "buttonFetchUrl4"
    OPEN_URLS_BUTTON_ID = "buttonOpenUrls"


