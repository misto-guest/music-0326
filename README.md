# Android Music Automation

Automated control system for managing multiple music apps on Android devices using UIAutomator2.

## Useful links

* How to use: https://sop.rebel.pm/sop/87
* [Phones usage sheet](https://docs.google.com/spreadsheets/d/1x_HFdN1BMOFoRGlGR1vqgsUQi_uBsnHfeadsVG4Ixyk/edit?gid=331104159#gid=331104159) 

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

Run the main script:
```bash
python -m src.main --device-id XXXXXXXXXXX
```

Run the main script with command:
```bash
python -m src.main --device-id XXXXXXXXXXX --command "sall --exclude amazon youtube"
```

To run all devices use launch.sh script in bash:
```bash
./launch.sh
```


## Testing

Run tests using pytest:
```bash
pytest tests/
```
