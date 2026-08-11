import logging
import logging.config
from pathlib import Path

_RESERVED_RECORD_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "message",
    "asctime",
}


class JsonLogFormatter(logging.Formatter):
    """Generic extra-field-passthrough JSON formatter.

    Any non-reserved field placed on a LogRecord via `extra=` (e.g. the
    `event`/`target` fields emitted by app.core.decorators.log_call) shows up
    automatically -- no formatter changes needed when a new decorated method
    is added anywhere in the codebase.
    """

    def format(self, record: logging.LogRecord) -> str:
        import json

        payload = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED_RECORD_ATTRS:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(level: str = "INFO", log_dir: str = "logs") -> None:
    """Configure logging once, at the very top of main.py before FastAPI()."""
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
            },
        }
    )
