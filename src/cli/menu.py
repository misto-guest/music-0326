# src/cli/menu.py

import sys
import time
import threading
import datetime
from typing import Dict, Callable, Optional, Any, List
from src.controllers.device_controller import DeviceController
from src.utils.logging_utils import setup_logger
from src.automation.multi_app_scheduler import MultiMusicAutomation
from src.constants.app_configs import YouTubeMusicConfig, AppleMusicConfig, AmazonMusicConfig, TidalMusicConfig

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

            # Tidal Music Controls
            't1': ('Tidal Music: Play/Pause',
                   lambda: self.controller.app_controllers['tidal_music'].play_pause()),
            't2': ('Tidal Music: Next Track',
                   lambda: self.controller.app_controllers['tidal_music'].next_track()),
            't3': ('Tidal Music: Previous Track',
                   lambda: self.controller.app_controllers['tidal_music'].previous_track()),
            't4': ('Tidal Music: IsoClipboard',
                   lambda: self.controller.app_controllers['tidal_music'].handle_isoclipboard()),
            't5': ('Tidal Music: Like Current Song',
                   lambda: self.controller.app_controllers['tidal_music'].like_current_song()),

            # Beatport Controls
            'b1': ('Beatport: Play/Pause',
                   lambda: self.controller.app_controllers['beatport_music'].play_pause()),
            'b2': ('Beatport: Next Track',
                   lambda: self.controller.app_controllers['beatport_music'].next_track()),
            'b3': ('Beatport: Previous Track',
                   lambda: self.controller.app_controllers['beatport_music'].previous_track()),
            'b4': ('Beatport: Initial Setup',
                   lambda: self.controller.app_controllers['beatport_music'].handle_initial_setup()),
            'b5': ('Beatport: Like Current Song',
                   lambda: self.controller.app_controllers['beatport_music'].like_current_song()),
            'b6': ('Beatport: Show Playtime Status',
                   lambda: self.controller.app_controllers['beatport_music'].check_daily_limit_reached()),

            # Single App Automation
            'sy': ('Start YouTube Music Only', self.start_youtube_automation),
            'sa': ('Start Apple Music Only', self.start_apple_automation),
            'sm': ('Start Amazon Music Only', self.start_amazon_automation),
            'st': ('Start Tidal Music Only', self.start_tidal_automation),
            'sb': ('Start Beatport Only', self.start_beatport_automation),

            # All Apps Automation
            'sall': ('Start All Apps', self.start_all_automation),

            # Automation Controls
            'stop': ('Stop Automation', self.stop_automation),
            'pause': ('Pause Automation', self.pause_automation),
            'resume': ('Resume Automation', self.resume_automation),
            'status': ('Show Automation Status', self.show_automation_status),

            # General Commands
            'c': ('Close Music Apps', self.controller.close_music_recent_apps),
            'r': ('Check Running Music Apps', self.controller.check_running_music_apps),
            'q': ('Quit', None)
        }

    def start_beatport_automation(self) -> bool:
        """Start Beatport automation only."""
        try:
            # First ensure initial setup is done
            beatport_controller = self.controller.app_controllers[
                'beatport_music']
            # Check if daily limit is already reached
            if beatport_controller.check_daily_limit_reached():
                logger.warning("Cannot start Beatport automation - daily limit already reached")
                return False

            # Perform initial setup if needed
            if not beatport_controller.is_running():
                logger.info("Performing initial Beatport setup...")
                if not beatport_controller.handle_initial_setup():
                    logger.error("Failed to set up Beatport")
                    return False

            # Initialize automation
            if not self.automation:
                logger.info("Initializing Beatport automation...")
                self.automation = MultiMusicAutomation(
                    beatport_controller=beatport_controller
                )

            success = self.automation.start_beatport_only()
            if success:
                logger.info("Beatport automation started successfully")
                return True
            else:
                logger.error("Failed to start Beatport automation")
                self.automation = None
                return False
        except Exception as e:
            logger.error(f"Failed to start Beatport automation: {e}")
            self.automation = None
            return False

    def start_tidal_automation(self) -> bool:
        """Start Tidal Music automation only."""
        try:
            if not self.automation:
                logger.info("Initializing Tidal Music automation...")
                self.automation = MultiMusicAutomation(
                    tidal_controller=self.controller.app_controllers['tidal_music']
                )
            success = self.automation.start_tidal_only()
            if success:
                logger.info("Tidal Music automation started successfully")
                return True
            else:
                logger.error("Failed to start Tidal Music automation")
                self.automation = None
                return False
        except Exception as e:
            logger.error(f"Failed to start Tidal Music automation: {e}")
            self.automation = None
            return False

    # Existing methods remain unchanged
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

    def start_all_automation(self, *args) -> bool:
        """
        Start automation for all apps with optional exclusions.

        Examples:
            sall                      -> starts all apps
            sall --exclude beatport   -> starts all apps except Beatport
            sall --exclude tidal      -> starts all apps except Tidal Music
            sall --exclude beatport tidal -> starts all apps except Beatport and Tidal
        """
        # If help flag is provided, print usage instructions.
        if args and args[0] in ['-h', '--help']:
            print(self.start_all_automation.__doc__)
            return True

        exclusions = set()
        if args:
            # Parse all arguments as potential exclusions (simpler syntax)
            for arg in args:
                if arg == '--exclude':
                    continue  # Skip the --exclude flag itself
                exclusion = arg.lower().strip('-')  # Remove any leading hyphens and normalize
                exclusions.add(exclusion)

        logger.info(f"Starting automation with exclusions: {exclusions}")

        # Map exclusions to controllers (adjust token names as needed)
        yt_controller = None if any(
            x in ['youtube', 'ytm', 'yt'] for x in exclusions) else self.controller.app_controllers.get('youtube_music')
        apple_controller = None if any(
            x in ['apple', 'am'] for x in exclusions) else self.controller.app_controllers.get('apple_music')
        amazon_controller = None if any(
            x in ['amazon', 'amz'] for x in exclusions) else self.controller.app_controllers.get('amazon_music')
        tidal_controller = None if 'tidal' in exclusions else self.controller.app_controllers.get('tidal_music')
        beatport_controller = None if 'beatport' in exclusions else self.controller.app_controllers.get('beatport')

        # Initialize automation with the filtered controllers.
        if not self.automation:
            logger.info("Initializing music apps automation...")
            self.automation = MultiMusicAutomation(
                youtube_controller=yt_controller,
                apple_controller=apple_controller,
                amazon_controller=amazon_controller,
                tidal_controller=tidal_controller,
                beatport_controller=beatport_controller
            )
        success = self.automation.start_automation()
        if success:
            logger.info("Music apps automation started successfully")
            return True
        else:
            logger.error("Failed to start music apps automation")
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
        """Show current automation status including pause state."""
        try:
            if self.automation:
                status = self.automation.get_status()
                logger.info(f"Automation status: {'Running' if status['running'] else 'Stopped'}")
                if status['paused']:
                    logger.info("Automation is currently paused")
                if status['running']:
                    # Log active apps first
                    logger.info(f"Active apps: {', '.join(status['active_apps'])}")
                    if 'YouTube Music' in status['active_apps']:
                        logger.info("YouTube Music Status:")
                        if 'last_youtube_action' in status:
                            logger.info(f"Last action: {status['last_youtube_action']}")
                        if 'next_youtube_iso' in status:
                            logger.info(f"Next IsoClipboard: {status['next_youtube_iso']}")

                    if 'Apple Music' in status['active_apps']:
                        logger.info("Apple Music Status:")
                        if 'last_apple_action' in status:
                            logger.info(f"Last action: {status['last_apple_action']}")
                        if 'next_apple_iso' in status:
                            logger.info(f"Next IsoClipboard: {status['next_apple_iso']}")

                    if 'Amazon Music' in status['active_apps']:
                        logger.info("Amazon Music Status:")
                        if 'last_amazon_action' in status:
                            logger.info(f"Last action: {status['last_amazon_action']}")
                        if 'next_amazon_iso' in status:
                            logger.info(f"Next IsoClipboard: {status['next_amazon_iso']}")

                    if 'Tidal Music' in status['active_apps']:
                        logger.info("Tidal Music Status:")
                        if 'last_tidal_action' in status:
                            logger.info(f"Last action: {status['last_tidal_action']}")
                        if 'next_tidal_iso' in status:
                            logger.info(f"Next IsoClipboard: {status['next_tidal_iso']}")

                    if 'Beatport' in status['active_apps']:
                        logger.info("Beatport Status:")
                        if 'beatport_hours_played' in status:
                            logger.info(
                                f"Hours played today: {status['beatport_hours_played']} / {status['beatport_daily_limit']}")
                            logger.info(f"Hours remaining: {status['beatport_hours_remaining']}")
                            if status['beatport_limit_reached']:
                                logger.warning("DAILY LIMIT REACHED - Playback restricted")
            else:
                logger.info("Automation status: Not initialized")
            return True
        except Exception as e:
            logger.error(f"Error showing automation status: {e}")
            return False

    def pause_automation(self) -> bool:
        """Pause the current automation."""
        try:
            if not self.automation:
                logger.warning("No automation is currently initialized")
                return False
            if not self.automation.running:
                logger.warning("No automation is currently running")
                return False
            if self.automation.paused:
                logger.warning("Automation is already paused")
                return False
            success = self.automation.pause_automation()
            if success:
                logger.info("Automation paused successfully")
            return success
        except Exception as e:
            logger.error(f"Failed to pause automation: {e}")
            return False

    def resume_automation(self) -> bool:
        """Resume the paused automation."""
        try:
            if not self.automation:
                logger.warning("No automation is currently initialized")
                return False
            if not self.automation.running:
                logger.warning("No automation is currently running")
                return False
            if not self.automation.paused:
                logger.warning("Automation is not paused")
                return False
            success = self.automation.resume_automation()
            if success:
                logger.info("Automation resumed successfully")
            return success
        except Exception as e:
            logger.error(f"Failed to resume automation: {e}")
            return False

    def display_menu(self, show_help: bool = False):
        """Display the main menu."""
        if not show_help:
            print("\nEnter command (use --help or -h to show all commands): ")
            return

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

        print("\nTidal Music Controls:")
        for key, (description, _) in self.commands.items():
            if key.startswith('t'):
                print(f"{key} - {description}")

        print("\nBeatport Controls:")
        for key, (description, _) in self.commands.items():
            if key.startswith('b'):
                print(f"{key} - {description}")

        print("\nAutomation Controls:")
        # Only show single-app and all-app automation commands
        single_app_commands = ['sy', 'sa', 'sm', 'st', 'sb', 'sall', 'stop', 'pause', 'resume', 'status']
        for key, (description, _) in self.commands.items():
            if key in single_app_commands:
                print(f"{key} - {description}")

        # Show special note about sall --exclude option
        print("\nNote: Use 'sall --exclude app1 app2' to start all apps except specified ones.")
        print("Example: 'sall --exclude beatport tidal' starts all apps except Beatport and Tidal")

        print("\nGeneral Commands:")
        for key, (description, _) in self.commands.items():
            if not key.startswith(('y', 'a', 'm', 't', 'b', 's')):
                print(f"{key} - {description}")

    def run(self):
        """Run the main CLI loop."""
        logger.info(f"Running CLI for device: {self.device_id}")
        while True:
            try:
                self.display_menu(show_help='--help' in sys.argv)
                command = input("\nEnter command: ").lower().strip()
                if command in ['--help', '-h']:
                    self.display_menu(show_help=True)
                    continue

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

    def handle_command(self, command: str) -> bool:
        parts = command.split()
        if not parts:
            return True
        cmd = parts[0]
        args = parts[1:]
        if cmd not in self.commands:
            logger.warning(f"Unknown command: {command}")
            return True

        description, func = self.commands[cmd]
        logger.info(f"Executing: {description}")
        try:
            result = func(*args) if args else func()
            if isinstance(result, bool) and not result:
                logger.error(f"Failed to execute: {description}")
            return True
        except Exception as e:
            logger.error(f"Error executing {description}: {e}")
            return True