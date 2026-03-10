#!/usr/bin/env python3
"""
Simple Flask API server for receiving track data
Run this on your server to receive track updates from track_monitor.py
"""

from flask import Flask, request, jsonify
import json
from datetime import datetime
import os

app = Flask(__name__)

# Store latest tracks in memory (replace with database for production)
latest_tracks = []
last_update = None

# Log file path
LOG_FILE = os.environ.get("LOG_FILE", "tracks.log")

@app.route('/api/track', methods=['POST'])
def receive_track():
    """Receive track data from monitors."""
    global latest_tracks, last_update
    
    try:
        data = request.get_json()
        
        if data and 'tracks' in data:
            latest_tracks = data['tracks']
            last_update = datetime.utcnow().isoformat()
            
            # Log to file
            with open(LOG_FILE, 'a') as f:
                f.write(f"\n--- {last_update} ---\n")
                for track in latest_tracks:
                    f.write(f"{track.get('device_id')}: {track.get('package')} - {track.get('track')} by {track.get('artist')} ({track.get('state')})\n")
            
            print(f"Received {len(latest_tracks)} tracks at {last_update}")
            return jsonify({"status": "ok", "tracks": len(latest_tracks)}), 200
        else:
            return jsonify({"status": "error", "message": "Invalid data format"}), 400
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/track', methods=['GET'])
def get_tracks():
    """Get current tracks."""
    return jsonify({
        "tracks": latest_tracks,
        "last_update": last_update
    })

@app.route('/api/health', methods=['GET'])
def health():
    """Health check."""
    return jsonify({"status": "healthy", "time": datetime.utcnow().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting track API server on port {port}...")
    print(f"Endpoint: POST /api/track")
    print(f"View tracks: GET /api/track")
    app.run(host='0.0.0.0', port=port, debug=False)
