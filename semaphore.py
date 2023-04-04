import functools
import logging
import time

from django.db.utils import IntegrityError

# module imports
from helpers.dateutils import local_now_tz_aware
# noinspection PyUnresolvedReferences
from helpers.misc import notimplemented_error

# local imports
from .models import SemaphoreRecord

log = logging.getLogger(__name__)

SEMAPHORE_LOCK_TIMEOUT_DEFAULT = 300.0;     'default semaphore lock timeout, in seconds'
SEMAPHORE_WAIT_TIMEOUT_DEFAULT = 300.0;     'default timeout waiting for semaphore lock'
SEMAPHORE_CALLBACK_DELAY_DEFAULT = 30;      'default delay between callbacks while waiting for semaphore'
SEMAPHORE_RETRIES_DELAY_DEFAULT = 0.3;      'default delay between retries to acquire a semaphore lock'


class SemaphoreLockedException(RuntimeError):
    def __init__(self, store: SemaphoreRecord):
        super().__init__(f"Semaphore '{store.key}' is locked since {store.locked.astimezone().isoformat()}")


class Semaphore:
    def __init__(self, key: str, timeout: float = SEMAPHORE_LOCK_TIMEOUT_DEFAULT):
        now = local_now_tz_aware()
        try:
            store = SemaphoreRecord.objects.get(pk=key)
            if store.locked and (now - store.pinged).total_seconds() < store.timeout:
                raise SemaphoreLockedException(store)

            records_updated = SemaphoreRecord.objects.filter(pk=key, modified=store.modified).update(
                pinged=now, locked=now, timeout=timeout, modified=now)
            store = SemaphoreRecord.objects.get(pk=key)

            if records_updated == 0:
                raise SemaphoreLockedException(store)

        except SemaphoreRecord.DoesNotExist:
            try:
                store = SemaphoreRecord.objects.create(
                    key=key,
                    timeout=timeout,
                    locked=now,
                    pinged=now
                )
            except IntegrityError:
                store = SemaphoreRecord.objects.get(pk=key)
                raise SemaphoreLockedException(store)

        self.store = store;  'database record of the semaphore'

    def ping(self):
        if not self.store:
            raise RuntimeError('semaphore is already released')
        self.store.pinged = local_now_tz_aware()
        self.store.save()

    def release(self):
        self.store.delete()
        self.store = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.store:
            self.release()

    @property
    def key(self):
        return self.store.key if self.store else None

    @property
    def timeout(self):
        return self.store.timeout if self.store else None

    @property
    def locked(self):
        return self.store.locked if self.store else False

    @property
    def pinged(self):
        return self.store.pinged if self.store else None


def semaphore(_func: callable = None, *, key: str = None, timeout: float = SEMAPHORE_LOCK_TIMEOUT_DEFAULT):
    def decorator(func: callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if key is None:
                args_repr = [repr(a) for a in args]
                kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
                signature = ", ".join(args_repr + kwargs_repr)
                sem_key = f"{func.__name__}({signature})"
            else:
                sem_key = key

            with Semaphore(key=sem_key, timeout=timeout) as sem:
                return func(*args, **kwargs, sem=sem)

        return wrapper

    if _func is None:
        return decorator
    else:
        return decorator(_func)


def semaphore_wait(
        key: str,
        sem_timeout: float = SEMAPHORE_LOCK_TIMEOUT_DEFAULT,
        wait_timeout: float = SEMAPHORE_WAIT_TIMEOUT_DEFAULT,
        callback: callable = lambda ex: None,
        cb_delay: float = SEMAPHORE_CALLBACK_DELAY_DEFAULT,
        retry_delay: float = SEMAPHORE_RETRIES_DELAY_DEFAULT
) -> Semaphore:
    """
    Waits for semaphore open and acquire the lock.
    @param key: semaphore key
    @param sem_timeout: semaphore lock timeout, in seconds
    @param wait_timeout: timeout waiting for semaphore lock, in seconds
    @param callback: called periodically during wait
    @param cb_delay: delay between callbacks while waiting for semaphore, in seconds
    @param retry_delay: delay between retries to acquire a semaphore lock
    @return: acquired Semaphore object
    """
    dt_start = local_now_tz_aware()
    dt_now = dt_start
    dt_last_callback = None
    last_exception = None
    while (dt_now - dt_start).total_seconds() < wait_timeout:
        try:
            sem = Semaphore(key=key, timeout=sem_timeout)
            return sem
        except SemaphoreLockedException as ex:
            last_exception = ex
            dt_now = local_now_tz_aware()
            if not dt_last_callback or (dt_now - dt_last_callback).total_seconds() > cb_delay:
                callback(ex)
                dt_last_callback = dt_now
            time.sleep(retry_delay)
    raise last_exception
