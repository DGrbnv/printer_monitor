import logging
from logging.handlers import RotatingFileHandler
import os
import time


def cleanup_logs(path: str, days: int = 3):
    if not os.path.exists(path):
        return
    if time.time() - os.path.getmtime(path) > days * 86400:
        os.remove(path)


def setup_logging(log_file: str, log_level: str):
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    level = getattr(logging, log_level.upper(), logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [file_handler, console_handler]
