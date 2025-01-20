# src/controllers/mutex_mixin.py

import threading
from functools import wraps
from typing import Callable
from src.utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class MutexMixin:
    """Mixin class providing mutex functionality for music controllers."""

    # Class-level mutex for device-wide synchronization
    _device_mutex = threading.Lock()

    def __init__(self, *args, **kwargs):
        """Initialize mutex mixin."""
        super().__init__(*args, **kwargs)
        self._app_mutex = threading.Lock()  # App-specific mutex

    def with_device_lock(self, func: Callable) -> Callable:
        """Decorator for functions requiring device-wide mutex."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                with self._device_mutex:
                    return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in device-locked operation {func.__name__}: {e}")
                return False

        return wrapper

    def with_app_lock(self, func: Callable) -> Callable:
        """Decorator for functions requiring app-specific mutex."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                with self._app_mutex:
                    return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in app-locked operation {func.__name__}: {e}")
                return False

        return wrapper