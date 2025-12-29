#src / main.py

import argparse
import logging
import sys
from pathlib import Path
import yaml
import subprocess
import re
from typing import List, Optional, Tuple
from src.cli.menu import CLI
from src.utils.logging_utils import setup_logger, set_log_file_name

logger = setup_logger(__name__)

def load_config():
    """Load configuration from YAML file."""
    config_path = Path(__file__).parent.parent / 'config' / 'devices_config.yaml'
    try:
        with open(config_path) as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return None


def get_device_id(config):
    """Get device ID from config or command line."""
    if config and 'devices' in config:
        default_device = next((d for d in config['devices'] if d.get('default', False)), None)
        if default_device:
            return default_device['id']
    return None


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Android Music Automation')
    parser.add_argument('--device-id', help='Android device ID')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--command', help='Command to run on start')
    return parser.parse_args()


def _adb_shell_capture(device_id: str, shell_cmd: str) -> str:
    """Run `adb -s <device_id> shell <cmd>` and capture stdout (best-effort)."""
    try:
        proc = subprocess.run(
            ["adb", "-s", device_id, "shell", shell_cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        logger.error("adb not found on PATH")
        return ""
    except Exception as e:
        logger.error(f"Failed running adb for user detection: {e}")
        return ""

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        if stderr:
            logger.warning(f"adb shell returned non-zero during user detection: {stderr}")
        return (proc.stdout or "").strip()
    return (proc.stdout or "").strip()


def detect_primary_and_work_profile_user_ids(device_id: str) -> Tuple[int, int]:
    """
    Detect the current (primary) Android user and a secondary/work-profile user id.

    Strategy:
      - Use `cmd user list` to find a managed/work profile if present.
      - Use `am get-current-user` for the current user.
      - Fallbacks preserve previous behavior (0, 11) if detection is inconclusive.
    """
    out = _adb_shell_capture(device_id, "cmd user list")
    all_users: List[int] = []
    managed_profile_users: List[int] = []

    if out:
        for line in out.splitlines():
            if "UserInfo{" not in line:
                continue
            m = re.search(r"UserInfo\{(\d+):", line)
            if not m:
                continue
            uid = int(m.group(1))
            all_users.append(uid)
            low = line.lower()
            if "profile" in low:
                managed_profile_users.append(uid)

    cur = _adb_shell_capture(device_id, "am get-current-user").strip()
    primary = int(cur) if cur.isdigit() else (all_users[0] if all_users else 0)

    secondary: Optional[int] = None
    for uid in managed_profile_users:
        if uid != primary:
            secondary = uid
            break

    if secondary is None:
        for uid in all_users:
            if uid != primary:
                secondary = uid
                break

    if secondary is None:
        secondary = 11 if primary != 11 else 0

    logger.info(f"Detected Android user IDs -> primary: {primary}, secondary: {secondary}")
    return primary, secondary


def main():
    """Main entry point."""
    args = parse_arguments()

    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level)

    # Load config and get device ID
    config = load_config()
    device_id = args.device_id or get_device_id(config)

    if not device_id:
        logger.error("No device ID provided. Please specify with --device-id")
        sys.exit(1)

    set_log_file_name(f"{device_id}.log")

    try:
        primary_uid, secondary_uid = detect_primary_and_work_profile_user_ids(device_id)
        cli = CLI(device_id, primary_uid, secondary_uid)
        cli.run(args.command)
    except KeyboardInterrupt:
        logger.info("\nExiting gracefully...")
    except Exception as e:
        logger.error(f"Error running CLI: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()