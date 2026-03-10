@echo off
REM Track Monitor Runner
REM Usage: run_track_monitor.bat [device_id]
REM   - No args: scans all devices
REM   - With device_id: monitors specific device

setlocal

REM Set API endpoint
set TRACK_API_ENDPOINT=https://your-dashboard.com/api/track

REM Enable debug output
set DEBUG=true

REM Get device ID if provided
if "%1"=="" (
    echo Scanning all devices...
    python track_monitor.py
) else (
    echo Monitoring device: %1
    set ANDROID_SERIAL=%1
    python track_monitor.py
)

endlocal
