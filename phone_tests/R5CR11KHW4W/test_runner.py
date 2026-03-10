#!/usr/bin/env python3
"""
Test Runner for Phone R5CR11KHW4W
Standalone script - does NOT touch production code
Usage: python test_runner.py
"""

import sys
import os
import time
import logging

# Add controllers to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uiautomator2 as u2
from controllers.apple_music import AppleMusicController

# Configuration
DEVICE_ID = "R5CR11KHW4W"
LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "test.log")

# Setup logging
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    print(f"\n{'='*60}")
    print(f"TEST RUNNER - Phone: {DEVICE_ID}")
    print(f"{'='*60}\n")
    
    # Connect
    logger.info(f"Connecting to device {DEVICE_ID}...")
    try:
        device = u2.connect(DEVICE_ID)
        logger.info(f"Connected: {device.info}")
    except Exception as e:
        logger.error(f"Failed to connect: {e}")
        return False
    
    # Create controller
    logger.info("Initializing Apple Music controller...")
    try:
        controller = AppleMusicController(device)
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        return False
    
    # Test 1: Login status
    print("\n--- Test 1: Login Status ---")
    logged_in, info = controller.check_login_status()
    print(f"Logged in: {logged_in} | {info}")
    
    # Test 2: Navigate to Library > Songs
    print("\n--- Test 2: Navigate to Library > Songs ---")
    nav_ok = controller.navigate_to_library_songs()
    print(f"Navigation: {'OK' if nav_ok else 'FAILED'}")
    
    # Test 3: Run full workflow
    print("\n--- Test 3: Full IsoClipboard + Shuffle Workflow ---")
    result = controller.handle_isoclipboard()
    print(f"Result: {'SUCCESS' if result else 'FAILED'}")
    
    # Test 4: Verify playback
    print("\n--- Test 4: Verify Playback ---")
    time.sleep(2)
    is_playing = controller.check_play_state()
    print(f"Playing: {is_playing}")
    
    # Test 5: Get current song
    print("\n--- Test 5: Current Song ---")
    song = controller.get_current_song()
    if song:
        print(f"Title: {song.get('title', 'Unknown')}")
        print(f"Artist: {song.get('artist', 'Unknown')}")
        print(f"Album: {song.get('album', 'Unknown')}")
    else:
        print("Could not retrieve song info")
    
    # Cleanup
    controller.cleanup()
    
    print(f"\n{'='*60}")
    print(f"TEST COMPLETE - Result: {'SUCCESS' if result and is_playing else 'FAILED'}")
    print(f"Log file: {LOG_FILE}")
    print(f"{'='*60}\n")
    
    return result and is_playing


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
