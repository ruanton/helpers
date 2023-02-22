import os
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
from collections.abc import Iterable
from requests.exceptions import ConnectionError
from urllib3.exceptions import ProtocolError, MaxRetryError, NewConnectionError

LOGING_FORMAT = '%(levelname)-8s [%(asctime)s] %(message)s'


def _json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError(f'Type {type(obj)} not serializable')


def json_dumps(obj) -> str:
    return simplejson.dumps(obj, indent=True, ensure_ascii=False, use_decimal=True, default=_json_serial)


def json_loads(data: str):
    return simplejson.loads(data, use_decimal=True)


def get_download_path():
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


def http_request(method, url, retries=5, random_retry_pause=0, **kwargs):
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


def get_logger(name: str = None):
    logging.basicConfig(format=LOGING_FORMAT, level=logging.INFO)
    return logging.getLogger(name if name else __name__)


def ignore_exceptions(_func: callable = None, *,
                      exceptions: typing.Type[Exception] | Iterable[typing.Type[Exception]] = Exception,
                      logger: logging.Logger = None, loglevel: int = logging.ERROR):

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
