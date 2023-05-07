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
import jsonpickle
from typing import Any
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


def jsonpickle_dumps(self) -> str:
    jsonpickle.set_encoder_options('simplejson', use_decimal=True, sort_keys=True, ensure_ascii=False, indent=4)
    jsonpickle.set_preferred_backend('simplejson')
    json_str = jsonpickle.dumps(self, use_decimal=True)
    return json_str


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


def is_integer(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    else:
        return float(value).is_integer()


RUSSIAN_ADDRESSES = {
    # Типы адресных объектов, допустимые для указания на уровне улиц.
    # Приказ МНС РФ от 02.12.2002 N БГ-3-04/686 "Об утверждении форм отчетности по налогу на доходы физических
    # лиц за 2002 год" (Зарегистрировано в Минюсте РФ 20.12.2002 N 4058).
    # source: https://www.consultant.ru/document/cons_doc_LAW_40112/560206dc56a17cb953bba43f466260f43e7f5107/
    'Аллея': 'аллея',
    'Бульвар': 'б-р',
    'Въезд': 'въезд',
    'Дорога': 'дор',
    'Животноводческая точка': 'жт',
    'Заезд': 'заезд',
    'Квартал': 'кв-л',
    'Километр': 'км',
    'Кольцо': 'кольцо',
    'Линия': 'линия',
    'Набережная': 'наб',
    'Остров': 'остров',
    'Парк': 'парк',
    'Переулок': 'пер',
    'Переезд': 'переезд',
    'Площадь': 'пл',
    'Площадка': 'пл-ка',
    'Проезд': 'проезд',
    'Проспект': 'пр-кт',
    'Просек': 'просек',
    'Проселок': 'проселок',
    'Проулок': 'проулок',
    'Сад': 'сад',
    'Сквер': 'сквер',
    'Строение': 'стр',
    'Территория': 'тер',
    'Тракт': 'тракт',
    'Тупик': 'туп',
    'Улица': 'ул',
    'Участок': 'уч-к',
    'Шоссе': 'Ш',
    'Аал': 'Аал',
    'Аул': 'Аул',
    'Выселки(ок)': 'Высел',
    'Городок': 'Городок',
    'Деревня': 'Д',
    'Железнодорожная будка': 'ж/д_будка',
    'Железнодорожная казарма': 'ж/д_казарм',
    'Ж/д остановочный (обгонный) пункт': 'ж/д_оп',
    'Железнодорожный пост': 'ж/д_пост',
    'Железнодорожный разъезд': 'ж/д_рзд',
    'Железнодорожная станция': 'ж/д_ст',
    'Казарма': 'казарма',
    'Местечко': 'м',
    'Микрорайон': 'мкр',
    'Населенный пункт': 'нп',
    'Платформа': 'платф',
    'Поселок сельского типа': 'п',
    'Почтовое отделение': 'п/о',
    'Планировочный район': 'п/р',
    'Поселок и (при) станция(и)': 'п/ст',
    'Полустанок': 'полустанок',
    'Починок': 'починок',
    'Разъезд': 'рзд',
    'Село': 'с',
    'Слобода': 'сл',
    'Станция': 'ст',
    'Хутор': 'х',
}


MAX_WIDTH_COMPACTED_VALUE = 120;  """Compaction is not performed if resulting string exceeds this size"""


def _compact_pickled_data(data: Any, remove_special: bool = True, remove_protected: bool = False) -> Any:
    """
    Compacts pickled data for simple visual representations.
    @param data: dict or list to compact
    @param remove_special: remove items with jsonpickle special keys
    @param remove_protected: remove items with keys starting with '_'
    @return: compacted and filtered data
    """

    def _value_is_empty(_val: Any) -> bool:
        return _val is None or _val in ('', 'none', 'null',) or _val == [] or _val == {}

    if isinstance(data, list):
        # compact every element of the list and remove empty elements
        data = [
            _compact_pickled_data(x, remove_special=remove_special, remove_protected=remove_protected)
            for x in data
        ]
        data = [x for x in data if not _value_is_empty(x)]

    if isinstance(data, list) and len(data) == 1:
        # convert list to single value
        return data[0]

    if isinstance(data, list) and len(data) <= 8 and all(not isinstance(x, dict | list) for x in data):
        # convert list to comma delimited string if short enough
        compacted = ', '.join([str(x) for x in data])
        return compacted if len(compacted) < MAX_WIDTH_COMPACTED_VALUE else data

    if isinstance(data, dict):
        # compact every element of the dictionary and remove elements with empty or special/protected values
        compacted = {}
        for key, value in data.items():
            value = _compact_pickled_data(value, remove_special=remove_special, remove_protected=remove_protected)
            if _value_is_empty(value):
                continue
            if remove_protected and key.startswith('_'):
                continue
            if remove_special and key in ('py/object', 'py/function', 'py/type',):
                continue
            compacted[key] = value
        data = compacted

    if isinstance(data, dict) and len(data) == 1:
        # collapse dict with inner dict if latter has single element
        key, val = list(data.items())[0]
        if isinstance(val, dict) and len(val) == 1:
            key_inner, val_inner = list(val.items())[0]
            data = {f'{key}=>{key_inner}': val_inner}

    if isinstance(data, dict) and len(data) <= 8 and all(not isinstance(x, dict | list) for x in data.values()):
        # convert list to comma delimited string with key=value pairs if short enough
        tokens = []
        for key, val in data.items():
            tokens.append(f'{key}={val}')
        compacted = ', '.join(tokens)
        return compacted if len(compacted) < MAX_WIDTH_COMPACTED_VALUE else data

    return data if not _value_is_empty(data) else None


def compact_debug_info(info: str, remove_protected: bool = False) -> str:
    """Compact and filter json pickled object for simplified visual representation"""
    if not info:
        return ''
    data = json_loads(info)
    compacted = _compact_pickled_data(data, remove_protected=remove_protected)
    return json_dumps(compacted)
