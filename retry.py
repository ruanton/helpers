import datetime
import time
import typing
import random
import logging
import functools
from collections.abc import Iterable

# local imports
from .misc import exception_descr
from .dateutils import local_now_tz_aware


def retry_callable(func: callable,
                   exceptions: typing.Type[Exception] | Iterable[typing.Type[Exception]] = Exception,
                   tries: int = None, timeout: float = None, random_pause: float = None,
                   logger: logging.Logger = None, loglevel: int = logging.WARN,
                   failures_nolog: int = None):
    """
    Calls given callable repeatedly until success
    :param func: callable to call
    :param exceptions: exception type or iterable of exception types to intercept
    :param tries: maximum number of tries; None - unlimited
    :param timeout: no retry after this number of seconds
    :param random_pause: wait before each retry with random delay within random_pause/2...random_pause*3/4 interval
    :param logger: if given, logs intercepted errors via this logger
    :param loglevel: level to log with
    :param failures_nolog: number first of failures not to log
    :return: what the callable returns
    """
    if tries is not None and tries <= 0:
        raise ValueError('tries must be positive integer or None')
    if timeout is not None and timeout <= 0:
        raise ValueError('timeout must be positive float or None')
    if random_pause is not None and random_pause <= 0:
        raise ValueError('random_pause must be positive float or None')
    if not tries and not timeout:
        raise ValueError('tries number or timeout must be given')
    if failures_nolog is not None and failures_nolog <= 0:
        raise ValueError('failures_nolog must be positive integer or None')

    if not isinstance(exceptions, Iterable):
        exceptions = [exceptions]

    dt_timeout = local_now_tz_aware() + datetime.timedelta(seconds=timeout) if timeout else None
    try_num = 1
    while True:
        # noinspection PyBroadException
        try:
            return func()
        except Exception as ex:
            if tries is not None and try_num >= tries:
                raise
            if not any(isinstance(ex, x) for x in exceptions):
                raise
            if timeout and local_now_tz_aware() > dt_timeout:
                raise
            retry_pause = random.uniform(random_pause*0.5, random_pause*1.5) if random_pause else None
            if logger and (failures_nolog is None or try_num > failures_nolog):
                if retry_pause:
                    logger.log(loglevel, f'{exception_descr(ex)}, will retry after {round(retry_pause, 2)} seconds...')
                    time.sleep(retry_pause)
                else:
                    logger.log(loglevel, f'{exception_descr(ex)}, retrying...')
            if retry_pause:
                time.sleep(retry_pause)
            try_num += 1


def retry(exceptions: typing.Type[Exception] | Iterable[typing.Type[Exception]] = Exception,
          tries: int = None, timeout: float = None, random_pause: float = None,
          logger: logging.Logger = None, loglevel: int = logging.WARN, failures_nolog: int = None):
    def decorator(func: callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return retry_callable(
                lambda: func(*args, **kwargs),
                exceptions=exceptions, tries=tries, timeout=timeout, random_pause=random_pause,
                logger=logger, loglevel=loglevel, failures_nolog=failures_nolog
            )
        return wrapper
    return decorator
