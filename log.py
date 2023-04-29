import logging

_default_formatter = logging.Formatter()
DB_LOGGER_ENABLE_FORMATTER = True

# config example for settings.py
"""
settings.LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {'format': '%(name)-12s %(levelname)-8s [%(asctime)s] - %(message)s', },
        'django.server': DEFAULT_LOGGING['formatters']['django.server'],
    },
    'handlers': {
        'console': { 'class': 'logging.StreamHandler', 'formatter': 'default', },
        'database': { 'level': 'DEBUG', 'class': 'helpers.log.DatabaseLogHandler' },
        'django.server': DEFAULT_LOGGING['handlers']['django.server'],
    },
    'loggers': {
        '': {  # default for all undefined Python modules
            'level': 'INFO',
            'handlers': ['console', 'database'],
        },
        'django.request': {  # logging 500 errors to database
            'handlers': ['database'],
            'level': 'ERROR',
            'propagate': False,  # avoid double logging because of root logger
        },
        'django.server': DEFAULT_LOGGING['loggers']['django.server'],  # default runserver request logging
    },
}
"""


class DatabaseLogHandler(logging.Handler):
    def emit(self, record):
        from .dba import Session, LogEntry
        with Session() as s:
            s.add(LogEntry(
                name=record.name,
                level=record.levelno,
                msg=self.format(record) if DB_LOGGER_ENABLE_FORMATTER else record.getMessage(),
                trace=_default_formatter.formatException(record.exc_info) if record.exc_info else '',
                task_id=getattr(record, 'task_id', ''),
                username=getattr(record, 'username', ''),
            ))
            s.commit()

        # from .models import LogEntry
        # LogEntry.objects.create(
        #     name=record.name,
        #     level=record.levelno,
        #     msg=self.format(record) if DB_LOGGER_ENABLE_FORMATTER else record.getMessage(),
        #     trace=_default_formatter.formatException(record.exc_info) if record.exc_info else '',
        #     task_id=getattr(record, 'task_id', ''),
        #     username=getattr(record, 'username', ''),
        # )

    def format(self, record):
        fmt = self.formatter if self.formatter else _default_formatter
        if type(fmt) == logging.Formatter:
            record.message = record.getMessage()

            if fmt.usesTime():
                record.asctime = fmt.formatTime(record, fmt.datefmt)

            # ignore exception traceback and stack info

            return fmt.formatMessage(record)

        else:
            return fmt.format(record)
