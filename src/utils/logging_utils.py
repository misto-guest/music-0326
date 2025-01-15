# src/utils/logging_utils.py

import logging
from typing import Optional


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with the specified name and level.

    Args:
        name: Logger name (typically __name__)
        level: Logging level

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)

    if not logger.handlers:  # Only add handler if none exists
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(level)
    return logger