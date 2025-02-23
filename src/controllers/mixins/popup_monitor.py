# src/controllers/mixins/popup_monitor.py

from src.controllers.mixins.singleton_popup_monitor import popup_monitor
from src.utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class PopupMonitorMixin:
    """Mixin class providing popup monitoring functionality using the singleton monitor."""

    def __init__(self, *args, **kwargs):
        """Initialize popup monitor mixin."""
        super().__init__(*args, **kwargs)
        # Get device from the base controller
        try:
            device = getattr(self, 'device', None)
            if device is None:
                logger.error("No device instance found in controller")
                return
            # Set device instance in singleton monitor if not already set
            if not hasattr(popup_monitor, 'device'):
                popup_monitor.set_device(device)
        except Exception as e:
            logger.error(f"Error initializing popup monitor mixin: {e}")

    def register_app_for_monitoring(self, app_name: str):
        """Register an app to be monitored for popups."""
        popup_monitor.register_app(app_name)

    def needs_restart(self, app_name: str) -> bool:
        """Check if an app needs to be restarted."""
        return popup_monitor.needs_restart(app_name)

    def clear_restart_flag(self, app_name: str):
        """Clear the restart flag for an app."""
        popup_monitor.clear_restart_flag(app_name)

    def start_popup_monitor(self):
        """Start the popup monitoring thread."""
        popup_monitor.start_monitor()

    def stop_popup_monitor(self):
        """Stop the popup monitoring thread."""
        popup_monitor.stop_monitor()