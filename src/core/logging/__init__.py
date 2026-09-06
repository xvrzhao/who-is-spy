import os, sys
import logging, logging.config

from src.core.config import settings


def setup_logging():
    os.makedirs("logs", exist_ok=True)

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,

        "formatters": {
            "default": {
                "()": "src.core.logging.formatters.colored_formatter.ColoredFormatter",
                "fmt": "[%(asctime)s] [%(levelname)s] <%(name)s> %(pathname)s:%(lineno)d (%(funcName)s): trace-id-%(trace_id)s | %(message)s",
            },
            "json": {
                "()": "src.core.logging.formatters.json_formatter.JSONFormatter",
            },
        },

        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json" if settings.is_production else "default",
                "stream": sys.stdout,
                "filters": ["trace"],
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": "logs/app.log",
                "maxBytes": 500 * 1024 * 1024,   # 500MB
                "backupCount": 10,
                "encoding": "utf-8",
                "filters": ["trace"],
            },
        },

        "filters": {
            "trace": {"()": "src.core.logging.filters.trace_filter.TraceFilter"},
        },

        "root": {
            "level": "DEBUG" if not settings.is_production else "INFO",
            "handlers": ["console"] if not settings.is_production else ["console", "file"],
        },

        "loggers": {
            "uvicorn": {"level": "INFO", "propagate": True},
            "uvicorn.access": {"level": "WARNING", "propagate": True},
            "httpcore": {"level": "INFO", "propagate": True},
            "sqlalchemy.engine": {"level": "WARNING", "propagate": True},
            "openai": {"level": "INFO", "propagate": True},
            "httpx": {"level": "WARNING", "propagate": True},
        },
    }

    logging.config.dictConfig(logging_config)
