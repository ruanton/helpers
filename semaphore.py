import functools
from django.db.utils import IntegrityError

from helpers.dateutils import local_now_tz_aware
from .models import SemaphoreRecord

SEMAPHORE_DEFAULT_TIMEOUT = 300.0  # timeout in seconds


class SemaphoreLockedException(RuntimeError):
    def __init__(self, store: SemaphoreRecord):
        super().__init__(f"Semaphore '{store.key}' is locked since {store.locked.astimezone().isoformat()}")


class Semaphore:
    def __init__(self, key: str, timeout: float = SEMAPHORE_DEFAULT_TIMEOUT):
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

        self.store = store

    def ping(self):
        self.store.pinged = local_now_tz_aware()
        self.store.save()

    def release(self):
        self.store.locked = None
        self.store.pinged = None
        self.store.save()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    @property
    def key(self):
        return self.store.key

    @property
    def timeout(self):
        return self.store.timeout

    @property
    def locked(self):
        return self.store.locked

    @property
    def pinged(self):
        return self.store.pinged


def semaphore(_func: callable = None, *, key: str = None, timeout: float = SEMAPHORE_DEFAULT_TIMEOUT):
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
