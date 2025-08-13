import subprocess
import logging
import re

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def check_apple_music_play_state(device_id: str) -> bool:
    try:
        cmd = f"adb -s {device_id} shell dumpsys media_session"
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            shell=True, text=True, encoding="utf-8", errors="ignore"
        )
        raw_output, error = process.communicate()

        if error:
            logger.error(f"ADB error: {error}")
            return False

        lines = raw_output.split("\n")
        apple_music_session = []
        capture = False

        for line in lines:
            if "MediaPlaybackService com.apple.android.music" in line:
                capture = True
            if capture:
                apple_music_session.append(line)
            if capture and line.strip() == "":
                # Empty line indicates end of block
                break

        if not apple_music_session:
            logger.debug("No active Apple Music session found.")
            return False

        # Print session for debugging
        print("\n=== FULL APPLE MUSIC SESSION ===")
        for line in apple_music_session:
            print(line)
        print("=== END OF SESSION ===\n")

        # Regex to find lines that look like: state=PlaybackState {state=PAUSED(2), ...
        pattern = re.compile(r"PlaybackState\s*\{state=(?:[A-Z]+)?\(?(\d+)\)?")

        for line in apple_music_session:
            if "state=PlaybackState" in line:
                match = pattern.search(line)
                if match:
                    numeric_state = int(match.group(1))
                    # 3 = PLAYING, 2 = PAUSED, 1 = STOPPED
                    is_playing = (numeric_state == 3)
                    logger.debug(
                        f"Apple Music Playback State: {numeric_state} -> is_playing={is_playing}"
                    )
                    return is_playing

        logger.debug("No playback state found in Apple Music session.")
        return False

    except Exception as e:
        logger.error(f"Error checking Apple Music play state: {e}")
        return False

if __name__ == "__main__":
    device_id = "RFCT5128G1D"
    is_playing = check_apple_music_play_state(device_id)
    print(f"Apple Music is playing: {is_playing}")
