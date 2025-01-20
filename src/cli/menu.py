# src/cli/menu.py

import time
from typing import Dict, Callable, Optional
from src.controllers.device_controller import DeviceController
from src.utils.logging_utils import setup_logger
from src.automation.multi_app_scheduler import MultiMusicAutomation

logger = setup_logger(__name__)


class CLI:
    """Command Line Interface for multi-app music automation."""

    def __init__(self, device_id: str):
        """Initialize CLI with device controller."""
        self.device_id = device_id
        self.controller = DeviceController(device_id)
        self.automation: Optional[MultiMusicAutomation] = None
        self._setup_commands()

    def _setup_commands(self):
        """Set up command mappings with app selection."""
        self.commands: Dict[str, tuple[str, Callable]] = {
            # YouTube Music controls
            'y1': ('YouTube Music: Play/Pause',
                   lambda: self.controller.app_controllers['youtube_music'].play_pause()),
            'y2': ('YouTube Music: Next Track',
                   lambda: self.controller.app_controllers['youtube_music'].next_track()),
            'y3': ('YouTube Music: Previous Track',
                   lambda: self.controller.app_controllers['youtube_music'].previous_track()),
            'y4': ('YouTube Music: Like Current Song',
                   lambda: self.controller.app_controllers['youtube_music'].like_current_song()),

            # Apple Music controls
            'a1': ('Apple Music: Play/Pause',
                   lambda: self.controller.app_controllers['apple_music'].play_pause()),
            'a2': ('Apple Music: Next Track',
                   lambda: self.controller.app_controllers['apple_music'].next_track()),
            'a3': ('Apple Music: Previous Track',
                   lambda: self.controller.app_controllers['apple_music'].previous_track()),
            'a4': ('Apple Music: Like Current Song',
                   lambda: self.controller.app_controllers['apple_music'].like_current_song()),

            # General commands
            'c': ('Close All Music Apps', self.controller.close_music_recent_apps),
            'r': ('Check Running Music Apps', self.controller.check_running_music_apps),
            'start': ('Start Multi-App Automation', self.start_automation),
            'stop': ('Stop Multi-App Automation', self.stop_automation),
            'status': ('Show Automation Status', self.show_automation_status),
            'q': ('Quit', None)
        }

    def start_automation(self):
        """Start the multi-app automation process."""
        try:
            if not self.automation:
                logger.info("Initializing multi-app automation...")
                self.automation = MultiMusicAutomation()

                # Add controllers for both music apps
                self.automation.add_controller(
                    'youtube_music',
                    self.controller.app_controllers['youtube_music']
                )
                self.automation.add_controller(
                    'apple_music',
                    self.controller.app_controllers['apple_music']
                )

            self.automation.start_automation()
            logger.info("Multi-app automation started successfully")

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
            active_apps = ", ".join(self.automation.controllers.keys())
            logger.info(f"Automation status: {status}")
            logger.info(f"Active music apps: {active_apps}")
        else:
            logger.info("Automation status: Not initialized")

    def display_menu(self):
        """Display the main menu with app-specific sections."""
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
        logger.info(f"Starting multi-app CLI for device: {self.device_id}")

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