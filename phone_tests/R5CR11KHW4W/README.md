# Phone Test Environment - R5CR11KHW4W

Standalone test scripts for phone R5CR11KHW4W. 
**Does NOT touch production code.**

## Structure

```
phone_tests/
  R5CR11KHW4W/
    controllers/
      apple_music.py      # Standalone controller (test version)
    logs/
      test.log            # Test logs
    test_runner.py        # Main test script
    README.md             # This file
  shared/
    ui_helpers.py         # (future) shared utilities
```

## Usage

From Windows MinGW or PowerShell:

```bash
cd C:\Users\windows2025\PycharmProjects\android_music_automation\phone_tests\R5CR11KHW4W
..\..\..\..\\.venv\Scripts\python.exe test_runner.py
```

Or with PM2-style convenience:

```bash
python test_runner.py
```

## What it does

1. Connects to phone R5CR11KHW4W
2. Checks Apple Music login status
3. Navigates to Library > Songs
4. Runs IsoClipboard + Shuffle workflow
5. Verifies playback
6. Reports current song

## Improvements over production

- **Multiple shuffle selectors**: content-desc, text, resource-id, class
- **KeyEvent fallback**: always works for basic playback
- **Better logging**: detailed step-by-step
- **Current song info**: shows what's playing

## Safety

- Completely isolated from production code
- Can be deleted without affecting main automation
- Logs go to separate folder

## To deploy to production

If tests succeed:
1. Copy `_click_shuffle_button()` method to production `apple_music.py`
2. Update selector strategy in `_handle_shuffle_and_miniplayer()`
3. Test on a few more phones before full rollout
