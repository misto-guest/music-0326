# src/controllers/mixins/popup_monitor.py

import threading
import time
from typing import Optional, Dict, Set
from src.utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class PopupMonitorMixin:
    """Mixin class providing popup monitoring functionality for Android apps."""

    def __init__(self, *args, **kwargs):
        """Initialize popup monitor."""
        super().__init__(*args, **kwargs)
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitor = threading.Event()
        self._monitor_lock = threading.Lock()
        self._app_needs_restart: Dict[str, bool] = {}
        self._monitored_apps: Set[str] = set()

    def register_app_for_monitoring(self, app_name: str):
        """Register an app to be monitored for popups."""
        self._monitored_apps.add(app_name)
        self._app_needs_restart[app_name] = False

    def needs_restart(self, app_name: str) -> bool:
        """Check if an app needs to be restarted."""
        return self._app_needs_restart.get(app_name, False)

    def clear_restart_flag(self, app_name: str):
        """Clear the restart flag for an app."""
        self._app_needs_restart[app_name] = False

    def start_popup_monitor(self):
        """Start the popup monitoring thread."""
        with self._monitor_lock:
            if self._monitor_thread and self._monitor_thread.is_alive():
                logger.warning("Popup monitor already running")
                return

            logger.info("Starting popup monitor")
            self._stop_monitor.clear()
            self._monitor_thread = threading.Thread(
                target=self._monitor_popups,
                name="PopupMonitor",
                daemon=True
            )
            self._monitor_thread.start()

    def stop_popup_monitor(self):
        """Stop the popup monitoring thread."""
        with self._monitor_lock:
            if self._monitor_thread and self._monitor_thread.is_alive():
                logger.info("Stopping popup monitor")
                self._stop_monitor.set()
                self._monitor_thread.join(timeout=5)
                if self._monitor_thread.is_alive():
                    logger.warning("Popup monitor thread did not stop gracefully")

    def _monitor_popups(self):
        """Main popup monitoring loop."""
        logger.info("Popup monitor started")
        while not self._stop_monitor.is_set():
            try:
                self._check_and_handle_popups()
                # Sleep with interrupt check
                for _ in range(10):  # 5 second sleep broken into 0.5s segments
                    if self._stop_monitor.is_set():
                        break
                    time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error in popup monitor: {e}")
                time.sleep(5)  # Sleep longer on error

    def _check_and_handle_popups(self):
        """Check for and handle any popups."""
        try:
            # Check for "isn't responding" popup
            if self.device(textContains="isn't responding").exists:
                popup_text = self.device(textContains="isn't responding").get_text()
                logger.warning(f"Detected app not responding popup: {popup_text}")

                if self.device(text="Close app").exists:
                    logger.info("Clicking 'Close app' by text")
                    self.device(text="Close app").click()
                elif self.device(resourceId="android:id/aerr_close").exists:
                    logger.info("Clicking 'Close app' by resource ID")
                    self.device(resourceId="android:id/aerr_close").click()
                else:
                    logger.error("Failed to find 'Close app' button by both text and resource ID")
                    return

                # Extract app name and mark for restart
                app_name = popup_text.split("isn't")[0].strip()
                logger.warning(f"Closed unresponsive app: {app_name}")

                # If it was one of our monitored apps, mark it for restart
                if app_name in self._monitored_apps:
                    logger.info(f"Will need to restart {app_name}")
                    self._app_needs_restart[app_name] = True

            # Check for other common popups
            self._check_additional_popups()

        except Exception as e:
            logger.error(f"Error handling popup: {e}")

    def _check_additional_popups(self):
        """Check for other types of popups that might need handling."""
        try:
            # Check for permissions popups
            if self.device(textContains="allow").exists and self.device(text="DENY").exists:
                logger.info("Detected permissions popup")
                if self.device(text="ALLOW").exists:
                    self.device(text="ALLOW").click()

            # Check for crash report popups
            if self.device(textContains="has stopped").exists:
                logger.warning("Detected crash popup")
                if self.device(text="OK").exists:
                    self.device(text="OK").click()

            # Check for "App is using battery" popups
            if self.device(textContains="battery").exists and self.device(text="OK").exists:
                logger.info("Detected battery usage popup")
                self.device(text="OK").click()

        except Exception as e:
            logger.error(f"Error checking additional popups: {e}")