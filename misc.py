import os
import io
import sys
import traceback
import simplejson
import datetime
import requests
import time
import random
import logging
import typing
import functools
import csv
from collections.abc import Iterable, Callable
from requests.exceptions import ConnectionError
from urllib3.exceptions import ProtocolError, MaxRetryError, NewConnectionError


def _json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError(f'Type {type(obj)} not serializable')


def json_dumps(obj) -> str:
    return simplejson.dumps(obj, indent=True, ensure_ascii=False, use_decimal=True, default=_json_serial)


def json_loads(data: str):
    return simplejson.loads(data, use_decimal=True)


def get_download_path() -> str:
    """Returns the default downloads path for linux or windows"""
    if os.name == 'nt':
        import winreg
        sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
        downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            location = winreg.QueryValueEx(key, downloads_guid)[0]
        return location
    else:
        return os.path.join(os.path.expanduser('~'), 'downloads')


def http_request(method: str, url: str, retries: int = 5, random_retry_pause: float = 0, **kwargs):
    while True:
        try:
            resp = requests.request(method, url, **kwargs)
            if resp.status_code == 200 or retries <= 0:
                if resp.status_code != 200:
                    raise RuntimeError(f'status_code={resp.status_code}')
                return resp
        except (ConnectionResetError, ProtocolError, ConnectionError, MaxRetryError, NewConnectionError, TimeoutError):
            if retries <= 0:
                raise
        if random_retry_pause > 0:
            time.sleep(random.uniform(random_retry_pause/2.0, random_retry_pause))
        retries -= 1


def exception_descr(ex, tb=None):
    exception_type = type(ex)
    exception_msg = ''.join(str(ex).strip().split('\n', 1)[:1]).strip()
    result = [f'{exception_type.__name__}({exception_msg})']

    if tb is None:
        _, e, tb = sys.exc_info()
        if e != ex:
            tb = None

    points = []
    for sframe in traceback.extract_tb(tb):
        filename = os.path.split(sframe.filename)[1]
        lineno = sframe.lineno
        if points and points[-1]['filename'] == filename:
            points[-1]['linenos'].append(str(lineno))
        else:
            points.append({'filename': filename, 'linenos': [str(lineno)]})

    if points:
        result.append(' in ')
        result.append(', '.join([f'{x["filename"]}({",".join(x["linenos"])})' for x in points]))

    return ''.join(result)


# noinspection PyUnusedLocal
def get_logger(name: str = None) -> logging.Logger:
    raise RuntimeError("""
    get_logger() deprecated, instead "log = get_logger()" do:

    in settings.py:
        LOGGING_FORMAT = '%(levelname)-8s [%(asctime)s] %(message)s'
        logging.basicConfig(format=LOGGING_FORMAT, level=logging.INFO)

    in each module:
        log = logging.getLogger(__name__)
    """)


def ignore_exceptions(
        _func: callable = None, *,
        exceptions: typing.Type[Exception] | Iterable[typing.Type[Exception]] = Exception,
        logger: logging.Logger = None, loglevel: int = logging.ERROR
):
    if not isinstance(exceptions, Iterable):
        exceptions = [exceptions]

    def decorator(func: callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as ex:
                if not any(isinstance(ex, x) for x in exceptions):
                    raise
                if logger:
                    logger.log(loglevel, exception_descr(ex))

        return wrapper

    if _func is None:
        return decorator
    else:
        return decorator(_func)


class FrozenClass(object):
    __frozen = False

    def __setattr__(self, key, value):
        if self.__frozen and not hasattr(self, key):
            raise TypeError(f'{self} is a frozen class')
        object.__setattr__(self, key, value)

    def freeze(self):
        self.__frozen = True

    def unfreeze(self):
        self.__frozen = False


def todict(obj, class_key=None):
    """
    Generic object to dict converter. Recursively convert.
    Useful for testing and asserting objects with expectation.
    Source: https://gist.github.com/sairamkrish/ab68be93b53b34c98e24908c67dfda0d
    """
    if isinstance(obj, dict):
        data = {}
        for (k, v) in obj.items():
            data[k] = todict(v, class_key)
        return data

    elif hasattr(obj, '_ast'):
        # noinspection PyProtectedMember
        return todict(obj._ast())

    elif hasattr(obj, '__iter__') and not isinstance(obj, str):
        return [todict(v, class_key) for v in obj]

    elif hasattr(obj, '__dict__'):
        data = dict([
            (key, todict(value, class_key)) for key, value in obj.__dict__.items()
            if not callable(value) and not key.startswith('_')
        ])
        if class_key is not None and hasattr(obj, "__class__"):
            data[class_key] = obj.__class__.__name__
        return data

    elif isinstance(obj, datetime.datetime):
        return obj.strftime("%Y-%m-%d %H:%M:%S%z")

    else:
        return obj


def notimplemented_error(*args):
    raise NotImplementedError(*args)


def iter_blocks(objects: list, size: int):
    """
    Create iterable for blocks of given size.

    @param objects: the list of objects
    @param size: size of a single block
    @return: generator of slices
    """
    offset = 0
    while offset < len(objects):
        yield objects[offset:offset+size]
        offset += size


def in_memory_csv(objects: Iterable, headers: Iterable[str], values: Callable[[object], Iterable]) -> io.StringIO:
    """
    Create in-memory CSV with given objects.

    @param objects: all objects to put in CSV
    @param headers: headers
    @param values: callable to get values from a single object
    """
    mem_csv = io.StringIO()
    writer = csv.writer(mem_csv)
    writer.writerow(headers)
    for obj in objects:
        writer.writerow(values(obj))
    mem_csv.seek(0)
    return mem_csv
