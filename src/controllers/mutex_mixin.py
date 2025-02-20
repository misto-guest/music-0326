# src/controllers/mutex_mixin.py

import threading
from functools import wraps
from typing import Callable
from src.utils.logging_utils import setup_logger

logger = setup_logger(__name__)

DEVICE_MUTEX = threading.Lock()

def with_device_lock(func: Callable) -> Callable:
    """Decorator for functions requiring device-wide mutex."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            with DEVICE_MUTEX:
                return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in device-locked operation {func.__name__}: {e}")
            return False
    return wrapper

def with_app_lock(lock: threading.Lock):
    """Decorator factory that returns a decorator requiring app-specific mutex."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                with lock:
                    return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in app-locked operation {func.__name__}: {e}")
                return False
        return wrapper
    return decorator

class MutexMixin:
    """Optional: Mixin class if you want each controller to have its own app lock."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._app_mutex = threading.Lock()

    @property
    def app_mutex(self):
        return self._app_mutex