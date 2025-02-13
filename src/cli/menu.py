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

            # Amazon Music Controls
            'm1': ('Amazon Music: Play/Pause',
                   lambda: self.controller.app_controllers['amazon_music'].play_pause()),
            'm2': ('Amazon Music: Next Track',
                   lambda: self.controller.app_controllers['amazon_music'].next_track()),
            'm3': ('Amazon Music: Previous Track',
                   lambda: self.controller.app_controllers['amazon_music'].previous_track()),
            'm4': ('Amazon Music: IsoClipboard',
                   lambda: self.controller.app_controllers['amazon_music'].handle_isoclipboard()),
            'm5': ('Amazon Music: Like Current Song',
                   lambda: self.controller.app_controllers['amazon_music'].like_current_song()),

            # Multi-App Automation Commands
            'sy': ('Start YouTube Music Only', self.start_youtube_automation),
            'sa': ('Start Apple Music Only', self.start_apple_automation),
            'sm': ('Start Amazon Music Only', self.start_amazon_automation),
            'sya': ('Start YouTube & Apple Music', self.start_youtube_apple_automation),
            'sym': ('Start YouTube & Amazon Music', self.start_youtube_amazon_automation),
            'sam': ('Start Apple & Amazon Music', self.start_apple_amazon_automation),
            'sall': ('Start All Apps', self.start_all_automation),
            'stop': ('Stop Automation', self.stop_automation),
            'status': ('Show Automation Status', self.show_automation_status),

            # General Commands
            'c': ('Close Music Apps', self.controller.close_music_recent_apps),
            'r': ('Check Running Music Apps', self.controller.check_running_music_apps),
            'q': ('Quit', None)
        }

    def start_youtube_automation(self) -> bool:
        """Start YouTube Music automation only."""
        try:
            if not self.automation:
                logger.info("Initializing YouTube Music automation...")
                self.automation = MultiMusicAutomation(
                    youtube_controller=self.controller.app_controllers['youtube_music']
                )
            success = self.automation.start_youtube_only()
            if success:
                logger.info("YouTube Music automation started successfully")
                return True
            else:
                logger.error("Failed to start YouTube Music automation")
                self.automation = None
                return False
        except Exception as e:
            logger.error(f"Failed to start YouTube Music automation: {e}")
            self.automation = None
            return False

    def start_apple_automation(self) -> bool:
        """Start Apple Music automation only."""
        try:
            if not self.automation:
                logger.info("Initializing Apple Music automation...")
                self.automation = MultiMusicAutomation(
                    apple_controller=self.controller.app_controllers['apple_music']
                )
            success = self.automation.start_apple_only()
            if success:
                logger.info("Apple Music automation started successfully")
                return True
            else:
                logger.error("Failed to start Apple Music automation")
                self.automation = None
                return False
        except Exception as e:
            logger.error(f"Failed to start Apple Music automation: {e}")
            self.automation = None
            return False

    def start_amazon_automation(self) -> bool:
        """Start Amazon Music automation only."""
        try:
            if not self.automation:
                logger.info("Initializing Amazon Music automation...")
                self.automation = MultiMusicAutomation(
                    amazon_controller=self.controller.app_controllers['amazon_music']
                )
            success = self.automation.start_amazon_only()
            if success:
                logger.info("Amazon Music automation started successfully")
                return True
            else:
                logger.error("Failed to start Amazon Music automation")
                self.automation = None
                return False
        except Exception as e:
            logger.error(f"Failed to start Amazon Music automation: {e}")
            self.automation = None
            return False

    def start_youtube_apple_automation(self) -> bool:
        """Start automation for YouTube Music and Apple Music."""
        try:
            if not self.automation:
                logger.info("Initializing YouTube & Apple Music automation...")
                self.automation = MultiMusicAutomation(
                    youtube_controller=self.controller.app_controllers['youtube_music'],
                    apple_controller=self.controller.app_controllers['apple_music']
                )
            success = self.automation.start_automation()
            if success:
                logger.info("YouTube & Apple Music automation started successfully")
                return True
            else:
                logger.error("Failed to start YouTube & Apple Music automation")
                self.automation = None
                return False
        except Exception as e:
            logger.error(f"Failed to start YouTube & Apple Music automation: {e}")
            self.automation = None
            return False

    def start_youtube_amazon_automation(self) -> bool:
        """Start automation for YouTube Music and Amazon Music."""
        try:
            if not self.automation:
                logger.info("Initializing YouTube & Amazon Music automation...")
                self.automation = MultiMusicAutomation(
                    youtube_controller=self.controller.app_controllers['youtube_music'],
                    amazon_controller=self.controller.app_controllers['amazon_music']
                )
            success = self.automation.start_automation()
            if success:
                logger.info("YouTube & Amazon Music automation started successfully")
                return True
            else:
                logger.error("Failed to start YouTube & Amazon Music automation")
                self.automation = None
                return False
        except Exception as e:
            logger.error(f"Failed to start YouTube & Amazon Music automation: {e}")
            self.automation = None
            return False

    def start_apple_amazon_automation(self) -> bool:
        """Start automation for Apple Music and Amazon Music."""
        try:
            if not self.automation:
                logger.info("Initializing Apple & Amazon Music automation...")
                self.automation = MultiMusicAutomation(
                    apple_controller=self.controller.app_controllers['apple_music'],
                    amazon_controller=self.controller.app_controllers['amazon_music']
                )
            success = self.automation.start_automation()
            if success:
                logger.info("Apple & Amazon Music automation started successfully")
                return True
            else:
                logger.error("Failed to start Apple & Amazon Music automation")
                self.automation = None
                return False
        except Exception as e:
            logger.error(f"Failed to start Apple & Amazon Music automation: {e}")
            self.automation = None
            return False

    def start_all_automation(self) -> bool:
        try:
            if not self.automation:
                logger.info("Initializing all music apps automation...")
                self.automation = MultiMusicAutomation(
                    youtube_controller=self.controller.app_controllers['youtube_music'],
                    apple_controller=self.controller.app_controllers['apple_music'],
                    amazon_controller=self.controller.app_controllers['amazon_music']
                )
            success = self.automation.start_automation()
            if success:
                logger.info("All music apps automation started successfully")
                return True
            else:
                logger.error("Failed to start all music apps automation")
                self.automation = None
                return False
        except Exception as e:
            logger.error(f"Failed to start all music apps automation: {e}")
            self.automation = None
            return False

    def stop_automation(self) -> bool:
        """Stop the automation process."""
        try:
            if self.automation:
                self.automation.stop_automation()
                logger.info("Automation stopped successfully")
                return True
            else:
                logger.warning("No automation running to stop")
                return False
        except Exception as e:
            logger.error(f"Failed to stop automation: {e}")
            return False

    def show_automation_status(self) -> bool:
        """Show current automation status."""
        try:
            if self.automation:
                status = "Running" if self.automation.running else "Stopped"
                logger.info(f"Automation status: {status}")
                if self.automation.running:
                    # Check which controllers are active
                    active_apps = []
                    if self.automation.youtube_controller:
                        yt_last = time.strftime('%H:%M:%S',
                                                time.localtime(self.automation.last_youtube_action))
                        yt_iso = time.strftime('%H:%M:%S',
                                               time.localtime(self.automation.last_youtube_isoclipboard))
                        active_apps.append("YouTube Music")
                        logger.info(f"Last YouTube Music action: {yt_last}")
                        logger.info(f"Last YouTube Music IsoClipboard: {yt_iso}")

                    if self.automation.apple_controller:
                        am_last = time.strftime('%H:%M:%S',
                                                time.localtime(self.automation.last_apple_action))
                        am_iso = time.strftime('%H:%M:%S',
                                               time.localtime(self.automation.last_apple_isoclipboard))
                        active_apps.append("Apple Music")
                        logger.info(f"Last Apple Music action: {am_last}")
                        logger.info(f"Last Apple Music IsoClipboard: {am_iso}")

                    if self.automation.amazon_controller:
                        amz_last = time.strftime('%H:%M:%S',
                                                 time.localtime(self.automation.last_amazon_action))
                        amz_iso = time.strftime('%H:%M:%S',
                                                time.localtime(self.automation.last_amazon_isoclipboard))
                        active_apps.append("Amazon Music")
                        logger.info(f"Last Amazon Music action: {amz_last}")
                        logger.info(f"Last Amazon Music IsoClipboard: {amz_iso}")

                    logger.info(f"Active apps: {', '.join(active_apps)}")
            else:
                logger.info("Automation status: Not initialized")
            return True
        except Exception as e:
            logger.error(f"Error showing automation status: {e}")
            return False

    def display_menu(self):
        print("\nYouTube Music Controls:")
        for key, (description, _) in self.commands.items():
            if key.startswith('y'):
                print(f"{key} - {description}")

        print("\nApple Music Controls:")
        for key, (description, _) in self.commands.items():
            if key.startswith('a'):
                print(f"{key} - {description}")

        print("\nAmazon Music Controls:")
        for key, (description, _) in self.commands.items():
            if key.startswith('m'):
                print(f"{key} - {description}")

        print("\nAutomation Controls:")
        for key, (description, _) in self.commands.items():
            if key in ['sy', 'sa', 'sm', 'sya', 'sym', 'sam', 'sall', 'stop', 'status']:
                print(f"{key} - {description}")

        print("\nGeneral Commands:")
        for key, (description, _) in self.commands.items():
            if not key.startswith(('y', 'a', 'm', 's')):
                print(f"{key} - {description}")

    def handle_command(self, command: str) -> bool:
        if command not in self.commands:
            logger.warning(f"Unknown command: {command}")
            return True

        description, func = self.commands[command]
        if func is None:  # Quit command
            return False

        try:
            logger.info(f"Executing: {description}")
            result = func()
            if isinstance(result, bool) and not result:
                logger.error(f"Failed to execute: {description}")
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