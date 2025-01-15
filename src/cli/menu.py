# src/cli/menu.py

import time
import logging
from typing import Dict, Callable
from src.controllers.device_controller import DeviceController
from src.utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class CLI:
    """Command Line Interface for music app automation."""

    def __init__(self, device_id: str):
        """Initialize CLI with device controller."""
        self.device_id = device_id
        self.controller = DeviceController(device_id)
        self._setup_commands()

    def _setup_commands(self):
        """Set up command mappings."""
        self.commands: Dict[str, tuple[str, Callable]] = {
            '1': ('Play/Pause Music',
                  lambda: self.controller.control_music_playback('youtube', 'play')),
            '2': ('Next Track',
                  lambda: self.controller.control_music_playback('youtube', 'next')),
            '3': ('Previous Track',
                  lambda: self.controller.control_music_playback('youtube', 'previous')),
            '4': ('IsoClipboard: YouTube Music',
                  lambda: self.controller.control_isoclipboard('youtube')),
            '4a': ('IsoClipboard: Apple Music',
                   lambda: self.controller.control_isoclipboard('apple')),
            '5': ('Like Current Song',
                  lambda: self.controller.control_music_playback('youtube', 'like')),
            '6': ('Close Music Apps',
                  self.controller.close_music_recent_apps),
            '7': ('Check Running Music Apps',
                  self.controller.check_running_music_apps),
            '8': ('Force Stop Music Apps',
                  self.controller.force_stop_music_apps),
            'q': ('Quit', None)
        }

    def display_menu(self):
        """Display the main menu."""
        print("\nControl Menu:")
        for key, (description, _) in self.commands.items():
            print(f"{key} - {description}")

    def handle_command(self, command: str) -> bool:
        """
        Handle user command.

        Returns:
            bool: False if should exit, True to continue
        """
        if command not in self.commands:
            logger.warning(f"Unknown command: {command}")
            return True

        description, func = self.commands[command]
        if func is None:  # Quit command
            return False

        try:
            logger.info(f"Executing: {description}")
            func()
            return True
        except Exception as e:
            logger.error(f"Error executing {description}: {e}")
            return True

    def run(self):
        """Run the main CLI loop."""
        logger.info(f"Starting CLI for device: {self.device_id}")

        while True:
            try:
                self.display_menu()
                command = input("Enter command: ").lower()

                if not self.handle_command(command):
                    logger.info("Exiting...")
                    break

                time.sleep(0.5)

            except KeyboardInterrupt:
                logger.info("\nReceived keyboard interrupt, exiting...")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                continue


def main():
    """Main entry point."""
    # TODO: Load device ID from config
    device_id = '26101JEGR05620'

    try:
        cli = CLI(device_id)
        cli.run()
    except Exception as e:
        logger.error(f"Failed to start CLI: {e}")
        raise


if __name__ == "__main__":
    main()