# src/cli/menu.py

import time
from typing import Dict, Callable, Optional
from src.controllers.device_controller import DeviceController
from src.utils.logging_utils import setup_logger
from src.automation.multi_app_scheduler import MultiMusicAutomation

logger = setup_logger(__name__)


class CLI:
    """Command Line Interface for music app automation."""

    def __init__(self, device_id: str):
        """Initialize CLI with device controller."""
        self.device_id = device_id
        logger.info(f"Initializing CLI for device: {device_id}")
        self.controller = DeviceController(device_id)
        self.automation: Optional[MultiMusicAutomation] = None
        self._setup_commands()

    def _setup_commands(self):
        """Set up command mappings."""
        self.commands: Dict[str, tuple[str, Callable]] = {
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
            'a6': ('Apple Music: Toggle Shuffle',
                   lambda: self.controller.app_controllers['apple_music'].shuffle()),

            # Automation Commands
            'sy': ('Start YouTube Music Automation', self.start_youtube_automation),
            'sa': ('Start Apple Music Automation', self.start_apple_automation),
            'sb': ('Start Both Apps Automation', self.start_automation),
            'stop': ('Stop Automation', self.stop_automation),
            'status': ('Show Automation Status', self.show_automation_status),

            # General Commands
            'c': ('Close Music Apps', self.controller.close_music_recent_apps),
            'r': ('Check Running Music Apps', self.controller.check_running_music_apps),
            'q': ('Quit', None)
        }

    def start_youtube_automation(self):
        """Start YouTube Music automation only."""
        try:
            if not self.automation:
                logger.info("Initializing YouTube Music automation...")
                self.automation = MultiMusicAutomation(
                    self.controller.app_controllers['youtube_music'],
                    None
                )
            self.automation.start_youtube_only()
            logger.info("YouTube Music automation started successfully")
        except Exception as e:
            logger.error(f"Failed to start YouTube Music automation: {e}")

    def start_apple_automation(self):
        """Start Apple Music automation only."""
        try:
            if not self.automation:
                logger.info("Initializing Apple Music automation...")
                self.automation = MultiMusicAutomation(
                    None,
                    self.controller.app_controllers['apple_music']
                )
            self.automation.start_apple_only()
            logger.info("Apple Music automation started successfully")
        except Exception as e:
            logger.error(f"Failed to start Apple Music automation: {e}")

    def start_automation(self):
        """Start automation for both apps."""
        try:
            if not self.automation:
                logger.info("Initializing multi-app automation...")
                self.automation = MultiMusicAutomation(
                    self.controller.app_controllers['youtube_music'],
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
            logger.info(f"Automation status: {status}")
            if self.automation.running:
                yt_last = time.strftime('%H:%M:%S', time.localtime(self.automation.last_youtube_action))
                am_last = time.strftime('%H:%M:%S', time.localtime(self.automation.last_apple_action))
                yt_iso = time.strftime('%H:%M:%S', time.localtime(self.automation.last_youtube_isoclipboard))
                am_iso = time.strftime('%H:%M:%S', time.localtime(self.automation.last_apple_isoclipboard))

                if self.automation.youtube_controller:
                    logger.info(f"Last YouTube Music action: {yt_last}")
                    logger.info(f"Last YouTube Music IsoClipboard: {yt_iso}")
                if self.automation.apple_controller:
                    logger.info(f"Last Apple Music action: {am_last}")
                    logger.info(f"Last Apple Music IsoClipboard: {am_iso}")
        else:
            logger.info("Automation status: Not initialized")

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

        print("\nAutomation Controls:")
        for key, (description, _) in self.commands.items():
            if key in ['sy', 'sa', 'sb', 'stop', 'status']:
                print(f"{key} - {description}")

        print("\nGeneral Commands:")
        for key, (description, _) in self.commands.items():
            if not key.startswith(('y', 'a')) and key not in ['sy', 'sa', 'sb', 'stop', 'status']:
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
        logger.info(f"Running CLI for device: {self.device_id}")

        while True:
            try:
                self.display_menu()
                command = input("\nEnter command: ").lower().strip()

                if not self.handle_command(command):
                    logger.info("Exiting...")
                    break

                time.sleep(0.5)

            except KeyboardInterrupt:
                logger.info("\nReceived keyboard interrupt, exiting...")
                self.stop_automation()
                break
            except Exception as e:
                logger.error(f"Error in CLI loop: {e}")
                continue