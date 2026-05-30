import logging
import os
from typing import Optional


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Create a consistent, structured logger for pipelines."""
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(log_level)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
