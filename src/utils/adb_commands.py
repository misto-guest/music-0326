# src/utils/adb_commands.py

import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def execute_adb_command(device_id: str, command: str) -> Optional[str]:
    """
    Execute an ADB command for a specific device.

    Args:
        device_id: The device identifier
        command: The ADB command to execute

    Returns:
        Optional[str]: Command output if successful, None otherwise
    """
    try:
        full_command = f"adb -s {device_id} {command}"
        result = subprocess.run(
            full_command.split(),
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"ADB command failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Error executing ADB command: {e}")
        return None