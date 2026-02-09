import os

LOGGING_CONFIG = {
    "level": os.getenv("LOGGING_LEVEL", "INFO"),
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        },
        "access": {
            "format": "%(asctime)s | %(levelname)s | uvicorn.access | %(message)s",
        },
    },
    "handlers": {
        "default": {"class": "logging.StreamHandler", "formatter": "default"},
        "access": {"class": "logging.StreamHandler", "formatter": "access"},
    },
    "loggers": {
        "": {"handlers": ["default"], "level": "INFO"},
        "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
        "app": {"handlers": ["default"], "level": "DEBUG", "propagate": False},
        "SteamClient": {"handlers": ["default"], "level": "INFO", "propagate": False},
    },
}