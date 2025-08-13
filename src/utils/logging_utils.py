# src/utils/logging_utils.py

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

def _old_setup_logger(name: str) -> logging.Logger:
    """Set up logger with proper configuration to avoid duplicate outputs."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # Create console handler
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Prevent propagation to avoid duplicate logs
        logger.propagate = False

    return logger


LOG_FILE_NAME = None

def set_log_file_name(name: str) -> None:
    global LOG_FILE_NAME
    LOG_FILE_NAME = name

    for name, logger in logging.Logger.manager.loggerDict.items():
        if isinstance(logger, logging.Logger):
            file_handler = create_file_handler()
            if not file_handler is None:
                logger.addHandler(file_handler)


def create_file_handler() -> logging.FileHandler | None:
    global LOG_FILE_NAME
    if LOG_FILE_NAME is None:
        return None

    log_dir: str = 'logs'
    max_bytes: int = 20 * 1024 * 1024
    backup_count: int = 10

    os.makedirs(log_dir, exist_ok=True)
    log_file = Path(log_dir) / f"{LOG_FILE_NAME}"
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create rotating file handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    return file_handler

def setup_logger(name: str) -> logging.Logger:
    global LOG_FILE_NAME

    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        file_handler = create_file_handler()
        if not file_handler is None:
            logger.addHandler(file_handler)

        # Prevent propagation to avoid duplicate logs
        logger.propagate = False

        logger.info(f"Logger initialized")


    return logger