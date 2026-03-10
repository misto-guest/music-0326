#!/usr/bin/env python3
"""
Test script for Apple Music shuffle functionality.
Uses the improved apple_music_test controller.
Safe to run - does not affect production code.

Usage:
    python test_apple_shuffle.py R5CR11KHW4W
"""

import sys
import time
import uiautomator2 as u2

# Import the test controller
from src.controllers.app_controllers.apple_music_test import AppleMusicController


def check_login_status(device) -> tuple:
    """Check if Apple Music is logged in. Returns (is_logged_in, account_info)."""
    print("\n--- Checking Apple Music Login Status ---")
    try:
        # Look for profile/account icon or sign-in prompt
        profile_selectors = [
            '//*[@resource-id="com.apple.android.music:id/profile_button"]',
            '//*[@resource-id="com.apple.android.music:id/account_button"]',
            '//*[contains(@content-desc, "profile") or contains(@content-desc, "account")]',
            '//*[contains(@text, "Sign In") or contains(@text, "Log In")]',
        ]
        
        for selector in profile_selectors:
            try:
                elem = device.xpath(selector)
                if elem.exists:
                    elem_text = elem.info.get('text', '')
                    elem_desc = elem.info.get('content-desc', '')
                    print(f"Found element: text='{elem_text}', desc='{elem_desc}'")
                    
                    # If we find "Sign In" text, user is NOT logged in
                    if 'sign in' in elem_text.lower() or 'log in' in elem_text.lower():
                        print("[FAIL] NOT LOGGED IN - Sign In button detected")
                        return False, "Sign In button found"
            except:
                continue
        
        # Try to access library to verify login
        # Navigate to Library tab
        library_tab = device.xpath('//*[@resource-id="com.apple.android.music:id/library_tab" or @text="Library" or @content-desc="Library"]')
        if library_tab.exists:
            library_tab.click()
            time.sleep(2)
            
            # Check for "All Songs" or similar content
            all_songs = device.xpath('//*[@text="Songs" or @text="All Songs" or @content-desc="Songs"]')
            if all_songs.exists:
                print("[OK] LOGGED IN - Library accessible")
                return True, "Library accessible"
        
        # Alternative: check if we can see "For You" or "Browse" tabs (requires login)
        for_you = device.xpath('//*[@text="For You" or @content-desc="For You"]')
        if for_you.exists:
            print("[OK] LOGGED IN - 'For You' tab visible")
            return True, "'For You' tab visible"
        
        print("[WARN] LOGIN STATUS UNCLEAR - Could not determine")
        return None, "Could not determine login status"
        
    except Exception as e:
        print(f"Error checking login status: {e}")
        return None, f"Error: {e}"


def navigate_to_library_all_songs(device) -> bool:
    """Navigate to Library > All Songs."""
    print("\n--- Navigating to Library > All Songs ---")
    try:
        # Step 1: Go to Library tab
        library_selectors = [
            '//*[@resource-id="com.apple.android.music:id/library_tab"]',
            '//*[@text="Library"]',
            '//*[@content-desc="Library"]',
            '//*[contains(@text, "Library")]',
        ]
        
        library_clicked = False
        for selector in library_selectors:
            try:
                library_tab = device.xpath(selector)
                if library_tab.exists:
                    library_tab.click()
                    print(f"Clicked Library tab")
                    library_clicked = True
                    break
            except:
                continue
        
        if not library_clicked:
            print("[WARN] Could not find Library tab, trying bottom navigation")
            # Try bottom nav
            device.shell("input tap 540 1850")  # Approximate library position
            time.sleep(1)
        
        time.sleep(2)
        
        # Step 2: Find and click "Songs" or "All Songs"
        songs_selectors = [
            '//*[@text="Songs"]',
            '//*[@text="All Songs"]',
            '//*[@content-desc="Songs"]',
            '//*[@content-desc="All Songs"]',
            '//*[contains(@text, "Songs")]',
        ]
        
        for selector in songs_selectors:
            try:
                songs_elem = device.xpath(selector)
                if songs_elem.exists:
                    songs_elem.click()
                    print(f"[OK] Clicked on Songs")
                    time.sleep(2)
                    return True
            except:
                continue
        
        # Alternative: scroll down to find Songs
        print("Trying to scroll to find Songs...")
        for _ in range(3):
            device.shell("input swipe 540 1200 540 600")
            time.sleep(1)
            for selector in songs_selectors:
                songs_elem = device.xpath(selector)
                if songs_elem.exists:
                    songs_elem.click()
                    print(f"[OK] Found and clicked Songs after scrolling")
                    time.sleep(2)
                    return True
        
        print("[WARN] Could not navigate to Library > Songs")
        return False
        
    except Exception as e:
        print(f"Error navigating to Library: {e}")
        return False


def get_current_song(device) -> dict:
    """Get information about currently playing song."""
    print("\n--- Getting Current Song Info ---")
    try:
        # Try mini-player first
        song_info = {}
        
        # Song title
        title_selectors = [
            '//*[@resource-id="com.apple.android.music:id/mini_player_song_title"]',
            '//*[@resource-id="com.apple.android.music:id/song_title"]',
            '//*[@resource-id="com.apple.android.music:id/title"]',
            '//*[contains(@resource-id, "song_title") or contains(@resource-id, "title")]',
        ]
        
        for selector in title_selectors:
            try:
                title_elem = device.xpath(selector)
                if title_elem.exists:
                    song_info['title'] = title_elem.info.get('text', 'Unknown')
                    break
            except:
                continue
        
        # Artist
        artist_selectors = [
            '//*[@resource-id="com.apple.android.music:id/mini_player_artist"]',
            '//*[@resource-id="com.apple.android.music:id/artist"]',
            '//*[contains(@resource-id, "artist")]',
        ]
        
        for selector in artist_selectors:
            try:
                artist_elem = device.xpath(selector)
                if artist_elem.exists:
                    song_info['artist'] = artist_elem.info.get('text', 'Unknown')
                    break
            except:
                continue
        
        if song_info:
            print(f"[SONG] Now Playing: {song_info.get('title', 'Unknown')} - {song_info.get('artist', 'Unknown')}")
        else:
            print("[WARN] Could not get song info from UI")
        
        return song_info
        
    except Exception as e:
        print(f"Error getting song info: {e}")
        return {}


def test_shuffle(device_id: str):
    """Test the improved shuffle functionality on a specific device."""
    print(f"\n{'='*60}")
    print(f"Testing Apple Music Shuffle on device: {device_id}")
    print(f"{'='*60}\n")

    # Connect to device
    print(f"Connecting to device {device_id}...")
    try:
        device = u2.connect(device_id)
        print(f"Connected! Device info: {device.info}")
    except Exception as e:
        print(f"ERROR: Failed to connect to device: {e}")
        return False

    # Create controller
    print("\nInitializing Apple Music controller (test version)...")
    try:
        controller = AppleMusicController(device)
        print("Controller initialized successfully")
    except Exception as e:
        print(f"ERROR: Failed to initialize controller: {e}")
        return False

    # Test 1: Check if Apple Music is installed
    print("\n--- Test 1: Check Apple Music installation ---")
    try:
        is_running = controller.is_running()
        print(f"Apple Music running: {is_running}")
    except Exception as e:
        print(f"Warning: Could not check running state: {e}")

    # Test 2: Prepare for action (brings AM to foreground)
    print("\n--- Test 2: Prepare for action ---")
    try:
        if controller.prepare_for_action():
            print("Successfully prepared for action")
        else:
            print("Warning: prepare_for_action returned False, continuing anyway...")
    except Exception as e:
        print(f"Warning: prepare_for_action failed: {e}")

    # Test 3: Check login status
    logged_in, login_info = check_login_status(device)
    
    # Test 4: Navigate to Library > All Songs
    if logged_in is not False:  # If logged in or unclear, try to navigate
        navigate_success = navigate_to_library_all_songs(device)
        if not navigate_success:
            print("[WARN] Could not navigate to Library > All Songs, continuing anyway...")
    else:
        print("[FAIL] Skipping navigation - user not logged in")

    # Test 5: Handle IsoClipboard and shuffle (the main test)
    print("\n--- Test 5: Handle IsoClipboard and Shuffle (main test) ---")
    print("This will test the improved shuffle button detection...")
    try:
        result = controller.handle_isoclipboard()
        if result:
            print("SUCCESS: handle_isoclipboard completed successfully!")
        else:
            print("FAILED: handle_isoclipboard returned False")
            print("Check logs above for details on which step failed")
    except Exception as e:
        print(f"ERROR: handle_isoclipboard threw exception: {e}")
        result = False

    # Test 6: Verify playback state and get song info
    print("\n--- Test 6: Verify playback state ---")
    time.sleep(2)
    try:
        is_playing = controller.check_play_state()
        print(f"Apple Music playing: {is_playing}")
        
        if is_playing:
            # Get current song
            time.sleep(2)
            song_info = get_current_song(device)
    except Exception as e:
        print(f"Could not verify play state: {e}")

    # Cleanup
    print("\n--- Cleanup ---")
    try:
        controller.stop_popup_monitor()
        print("Stopped popup monitor")
    except Exception as e:
        print(f"Warning: cleanup error: {e}")

    print(f"\n{'='*60}")
    print(f"Test completed. Result: {'SUCCESS' if result else 'FAILED'}")
    if logged_in is False:
        print(f"[WARN] LOGIN ISSUE: {login_info}")
    print(f"{'='*60}\n")

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_apple_shuffle.py <device_id>")
        print("Example: python test_apple_shuffle.py R5CR11KHW4W")
        sys.exit(1)

    device_id = sys.argv[1]
    success = test_shuffle(device_id)
    sys.exit(0 if success else 1)
