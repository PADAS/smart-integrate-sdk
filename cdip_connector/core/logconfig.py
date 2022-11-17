import logging
import logging.config
import sys


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": "%(asctime)s %(levelname)s %(processName)s %(thread)d %(name)s %(message)s",
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "json",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
        "PIL.Image": {
            "level": "INFO",
        },
    },
}

try:
    # local_log.py should contain an override of DEFAULT_LOGGING as seen below
    from .local_log_settings import LOGGING_CONFIG

except ImportError:
    local_log = None

has_initialized = False


def init():
    """
    Initialize logging using the default LOGGING_CONFIG above or using an alternative
    imported from .local_log_settings
    :return:
    """

    global has_initialized
    has_initialized = True

    global LOGGING_CONFIG
    logging.config.dictConfig(LOGGING_CONFIG)

    global init
    init = lambda: "already initialized"
