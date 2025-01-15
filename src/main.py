# src/main.py

import argparse
import logging
import sys
from pathlib import Path
import yaml

from src.cli.menu import CLI
from src.utils.logging_utils import setup_logger

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
    return parser.parse_args()


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

    try:
        cli = CLI(device_id)
        cli.start_automation()
        cli.run()
    except KeyboardInterrupt:
        logger.info("\nExiting gracefully...")
    except Exception as e:
        logger.error(f"Error running CLI: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()