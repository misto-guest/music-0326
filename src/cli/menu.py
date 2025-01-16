# src/cli/menu.py

import time
from typing import Dict, Callable, Optional, Tuple
from src.controllers.device_controller import DeviceController
from src.utils.logging_utils import setup_logger
from src.automation.music_scheduler import MusicAutomation

logger = setup_logger(__name__)


class CLI:
    """Command Line Interface for music app automation."""

    def __init__(self, device_id: str):
        """Initialize CLI with device controller."""
        self.device_id = device_id
        self.controller = DeviceController(device_id)
        self.automation: Optional[MusicAutomation] = None
        self._setup_commands()

    def _setup_commands(self):
        """Set up command mappings."""
        self.commands: Dict[str, Tuple[str, Callable]] = {
            '1': ('Play/Pause Music',
                  lambda: self.controller.app_controllers['youtube_music'].play_pause()),
            '2': ('Next Track',
                  lambda: self.controller.app_controllers['youtube_music'].next_track()),
            '3': ('Previous Track',
                  lambda: self.controller.app_controllers['youtube_music'].previous_track()),
            '4': ('IsoClipboard: YouTube Music',
                  lambda: self.controller.app_controllers['youtube_music'].handle_isoclipboard()),
            '5': ('Like Current Song',
                  lambda: self.controller.app_controllers['youtube_music'].like_current_song()),
            '6': ('Close Music Apps',
                  self.controller.close_music_recent_apps),
            '7': ('Check Running Music Apps',
                  self.controller.check_running_music_apps),
            'a': ('Start Automation', self.start_automation),
            's': ('Stop Automation', self.stop_automation),
            'status': ('Show Automation Status', self.show_automation_status),
            'q': ('Quit', None)
        }

    def start_automation(self):
        """Start the automation process."""
        try:
            if not self.automation:
                logger.info("Initializing automation...")
                self.automation = MusicAutomation(self.controller.app_controllers['youtube_music'])
            self.automation.start_automation()
            logger.info("Automation started successfully")
        except Exception as e:
            logger.error(f"Failed to start automation: {e}")

    def stop_automation(self):
        """Stop the automation process."""
        try:
            if self.automation:
                self.automation.stop_automation()
                logger.info("Automation stopped successfully")
            else:
                logger.warning("No automation running to stop")
        except Exception as e:
            logger.error(f"Failed to stop automation: {e}")

    def show_automation_status(self):
        """Show current automation status."""
        if self.automation:
            status = "Running" if self.automation.running else "Stopped"
        else:
            status = "Not initialized"
        logger.info(f"Automation status: {status}")

    def display_menu(self):
        """Display the main menu."""
        print("\nControl Menu:")
        for key, (description, _) in self.commands.items():
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
                self.stop_automation()  # Stop automation on exit
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                continue