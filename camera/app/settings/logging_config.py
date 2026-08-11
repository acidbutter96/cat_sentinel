"""dictConfig-based logging setup, called once at startup before the FastAPI
app instance is created.
"""

from __future__ import annotations

import logging.config
from pathlib import Path


def setup_logging(level: str = "INFO", log_dir: str = "logs") -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "console": {"class": "logging.StreamHandler", "formatter": "default"},
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "default",
                    "filename": str(Path(log_dir) / "app.log"),
                    "maxBytes": 10_000_000,
                    "backupCount": 5,
                },
            },
            "root": {"handlers": ["console", "file"], "level": level},
            "loggers": {
                "sqlalchemy.engine": {"level": "WARNING", "propagate": True},
                "uvicorn.access": {"level": "INFO", "propagate": True},
                "av": {"level": "WARNING", "propagate": True},
            },
        }
    )
