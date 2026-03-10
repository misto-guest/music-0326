#!/usr/bin/env python3
"""
Track Monitoring Script for Music Automation
Queries all active media sessions and forwards to dashboard API
"""

import subprocess
import json
import requests
import re
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional

# Configuration
API_ENDPOINT = os.environ.get("TRACK_API_ENDPOINT", "")
DEVICE_ID = os.environ.get("ANDROID_SERIAL", "")
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"  # Print only, don't send

# Use Windows ADB from WSL
def run_adb(args: List[str], timeout: int = 30) -> str:
    """Run ADB command on Windows via cmd.exe."""
    cmd = ["adb"] + args
    # Use full path to cmd.exe
    result = subprocess.run(
        ["/mnt/c/Windows/System32/cmd.exe", "/c", " ".join(cmd)],
        capture_output=True,
        text=True,
        timeout=timeout
    )
    return result.stdout

def get_adb_devices() -> List[str]:
    """Get list of connected Android devices."""
    try:
        output = run_adb(["devices"])
        devices = []
        for line in output.strip().split("\n")[1:]:
            if line.strip() and "device" in line and "unauthorized" not in line:
                device = line.split()[0]
                devices.append(device)
        return devices
    except Exception as e:
        print(f"Error getting devices: {e}")
        return []

def parse_media_session(device_id: str) -> List[Dict]:
    """Parse media session output for a device."""
    sessions = []
    
    try:
        output = run_adb(["-s", device_id, "shell", "dumpsys", "media_session"])
        
        # Find all session blocks
        session_pattern = r'(MediaPlaybackService|MusicService|androidx\.media3\.session\.id\.)\s+(\S+)/(\S+)\s+\(userId=(\d+)\)'
        state_pattern = r'state=PlaybackState\s*\{state=(\w+)\((\d+)\)[^}]*position=(\d+)'
        metadata_pattern = r'metadata:\s*size=(\d+),\s*description=([^,\n]+),\s*([^,\n]+),\s*([^\n]+)'
        
        # Split by sessions
        current_package = None
        current_user = None
        current_state = None
        current_position = None
        current_track = None
        current_artist = None
        current_album = None
        
        for line in output.split("\n"):
            # Detect new session
            match = re.search(session_pattern, line)
            if match:
                # Save previous session if exists and playing
                if current_package and current_state in ["PLAYING", "3"]:
                    sessions.append({
                        "device_id": device_id,
                        "package": current_package,
                        "user_id": current_user,
                        "state": current_state,
                        "position": current_position,
                        "track": current_track,
                        "artist": current_artist,
                        "album": current_album,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                # Reset for new session
                current_package = match.group(3)  # package name
                current_user = match.group(4)
                current_state = None
                current_position = None
                current_track = None
                current_artist = None
                current_album = None
            
            # Parse state
            if "state=PlaybackState" in line:
                state_match = re.search(state_pattern, line)
                if state_match:
                    state_name = state_match.group(1)
                    state_num = state_match.group(2)
                    current_position = state_match.group(3)
                    # Convert state number to name
                    state_map = {"0": "NONE", "1": "STOPPED", "2": "PAUSED", "3": "PLAYING", "7": "ERROR"}
                    current_state = state_map.get(state_num, state_name)
            
            # Parse metadata (track info)
            if "description=" in line and "size=" in line:
                try:
                    # Format: description=Track, Artist, Album
                    desc_match = re.search(r'description=([^,\n]+),\s*([^,\n]+),\s*([^\n]+)', line)
                    if desc_match:
                        current_track = desc_match.group(1).strip()
                        current_artist = desc_match.group(2).strip()
                        current_album = desc_match.group(3).strip()
                except:
                    pass
        
        # Don't forget last session
        if current_package and current_state in ["PLAYING", "3"]:
            sessions.append({
                "device_id": device_id,
                "package": current_package,
                "user_id": current_user,
                "state": current_state,
                "position": current_position,
                "track": current_track,
                "artist": current_artist,
                "album": current_album,
                "timestamp": datetime.utcnow().isoformat()
            })
                
    except Exception as e:
        print(f"Error parsing media session for {device_id}: {e}")
    
    return sessions

def send_to_api(sessions: List[Dict]) -> bool:
    """Send track data to API endpoint."""
    if not sessions:
        return True
    
    if DRY_RUN:
        print(f"[DRY RUN] Would send {len(sessions)} tracks to API:")
        for s in sessions:
            print(f"  - {s['device_id']}: {s['package']}: {s['track']} - {s['artist']} ({s['state']})")
        return True
    
    if not API_ENDPOINT:
        print("No API_ENDPOINT set, skipping send")
        return True
    
    try:
        response = requests.post(
            API_ENDPOINT,
            json={"tracks": sessions},
            timeout=10
        )
        if response.status_code in [200, 201, 202]:
            if DEBUG:
                print(f"Successfully sent {len(sessions)} tracks to API")
            return True
        else:
            print(f"API returned {response.status_code}: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error sending to API: {e}")
        return False

def main():
    """Main function."""
    all_sessions = []
    
    # Determine which devices to check
    if DEVICE_ID:
        devices = [DEVICE_ID]
    else:
        devices = get_adb_devices()
    
    if DEBUG:
        print(f"Checking {len(devices)} devices...")
    
    for device in devices:
        sessions = parse_media_session(device)
        all_sessions.extend(sessions)
        
        if DEBUG and sessions:
            print(f"\n{device}:")
            for s in sessions:
                print(f"  - {s['package']}: {s['track']} - {s['artist']} ({s['state']})")
    
    # Send to API
    if all_sessions:
        success = send_to_api(all_sessions)
        if DEBUG:
            print(f"\nTotal: {len(all_sessions)} playing tracks")
        return 0 if success else 1
    else:
        if DEBUG:
            print("No tracks currently playing")
        return 0

if __name__ == "__main__":
    sys.exit(main())
