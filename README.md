# Android Music Automation

Automated control system for managing multiple music apps on Android devices using UIAutomator2.

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd android_music_automation
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install requirements:
```bash
pip install -r requirements.txt
```

## Usage

https://sop.rebel.pm/sop/87

Run the main script:
```bash
python -m src.main --device-id XXXXXXXXXXX
```

## Testing

Run tests using pytest:
```bash
pytest tests/
```
