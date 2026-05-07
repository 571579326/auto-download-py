import logging
import os
from logging.handlers import RotatingFileHandler

from app.core.config import get_settings


def setup_logging() -> None:
    settings = get_settings()
    os.makedirs(os.path.dirname(settings.log_file), exist_ok=True)

    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root_logger.setLevel(level)

    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s %(threadName)s %(message)s'
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    file_handler = RotatingFileHandler(
        settings.log_file,
        maxBytes=50 * 1024 * 1024,
        backupCount=20,
        encoding='utf-8',
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
