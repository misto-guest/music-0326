# phone_tests/R5CR11KHW4W/config.py
# Phone-specific configuration

DEVICE_ID = "R5CR11KHW4W"
PANDA_INDEX = 5  # Index in Panda app

# Music apps to run
APPS = {
    "apple_music": True,
    "youtube_music": False,  # excluded
    "amazon_music": False,   # excluded
    "tidal_music": False,    # excluded
    "beatport_music": True,
}

# Shuffle selectors (from UI dump analysis)
SHUFFLE_SELECTORS = [
    '//*[@content-desc="play shuffled"]',  # Library view shuffle button
    '//*[@content-desc="Shuffle On"]',     # Player shuffle toggle (on)
    '//*[@content-desc="Shuffle Off"]',    # Player shuffle toggle (off)
    '//*[@resource-id="com.apple.android.music:id/button_shuffle" and contains(@class, "LinearLayout")]',  # By class
    '//*[@text="Shuffle"]',                 # By text
]

# IsoClipboard config
ISOCLIPBOARD_PACKAGE = "com.example.isolatedclipboard"
ISOCLIPBOARD_FETCH_BUTTON = "com.example.isolatedclipboard:id/buttonFetchUrl2"

# Timeouts
FETCH_WAIT_SECONDS = 15
SHUFFLE_WAIT_SECONDS = 3
PLAYBACK_CHECK_RETRIES = 3
