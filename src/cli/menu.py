# src/cli/menu.py

import time
import argparse
from typing import Dict, Callable, Optional, Tuple
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
        self.commands: Dict[str, Tuple[str, Callable]] = {
            # YouTube Music Controls
            'y1': ('YouTube Music: Play/Pause',
                   lambda: self.controller.app_controllers['youtube_music'].play_pause()),
            'y2': ('YouTube Music: Next Track',
                   lambda: self.controller.app_controllers['youtube_music'].next_track()),
            'y3': ('YouTube Music: Previous Track',
                   lambda: self.controller.app_controllers['youtube_music'].previous_track()),
            'y4': ('YouTube Music: IsoClipboard',
                   lambda: self.controller.app_controllers['youtube_music'].handle_isoclipboard()),
            'y5': ('YouTube Music: Like Current Song',
                   lambda: self.controller.app_controllers['youtube_music'].like_current_song()),

            # Apple Music Controls
            'a1': ('Apple Music: Play/Pause',
                   lambda: self.controller.app_controllers['apple_music'].play_pause()),
            'a2': ('Apple Music: Next Track',
                   lambda: self.controller.app_controllers['apple_music'].next_track()),
            'a3': ('Apple Music: Previous Track',
                   lambda: self.controller.app_controllers['apple_music'].previous_track()),
            'a4': ('Apple Music: IsoClipboard',
                   lambda: self.controller.app_controllers['apple_music'].handle_isoclipboard()),
            'a5': ('Apple Music: Like Current Song',
                   lambda: self.controller.app_controllers['apple_music'].like_current_song()),

            # General Commands
            'c': ('Close Music Apps', self.controller.close_music_recent_apps),
            'r': ('Check Running Music Apps', self.controller.check_running_music_apps),
            'q': ('Quit', None)
        }

    def display_menu(self):
        """Display the main menu."""
        print("\nYouTube Music Controls:")
        for key, (description, _) in self.commands.items():
            if key.startswith('y'):
                print(f"{key} - {description}")

        print("\nApple Music Controls:")
        for key, (description, _) in self.commands.items():
            if key.startswith('a'):
                print(f"{key} - {description}")

        print("\nGeneral Commands:")
        for key, (description, _) in self.commands.items():
            if not key.startswith(('y', 'a')):
                print(f"{key} - {description}")

    def handle_command(self, command: str) -> bool:
        """Handle user command."""
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