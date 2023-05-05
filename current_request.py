"""
Modified copy of django-currentuser - https://github.com/PaesslerAG/django-currentuser

Add it to the middleware classes in your settings.py:
    MIDDLEWARE = (
        ...,
        'helpers.current_request.ThreadCurrentRequestMiddleware',
    )
"""

import logging
import threading
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, AbstractUser
from django.http.request import HttpRequest

CURRENT_REQUEST_ATTR_NAME = getattr(settings, 'CURRENT_REQUEST_ATTR_NAME', '_current_request')

_thread_locals = threading.local()


def _do_set_current_request(request_func):
    setattr(_thread_locals, CURRENT_REQUEST_ATTR_NAME, request_func.__get__(request_func, threading.local))


def _set_current_request(request: HttpRequest = None):
    """
    Sets current request in local thread.

    Can be used as a hook e.g. for shell jobs (when request object is not available).
    """
    _do_set_current_request(lambda x: request)


class SetCurrentRequest:
    def __init__(self, request):
        self.request = request

    def __enter__(self):
        _do_set_current_request(lambda x: self.request)

    def __exit__(self, exception_type, exception_value, exception_traceback):
        _do_set_current_request(lambda x: None)


class ThreadCurrentRequestMiddleware(object):

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        with SetCurrentRequest(request):
            response = self.get_response(request)
        return response


def get_current_request() -> HttpRequest | None:
    """
    @return: current django request object in the local thread if any.
    """
    current_request = getattr(_thread_locals, CURRENT_REQUEST_ATTR_NAME, None)
    if callable(current_request):
        current_request = current_request()
    assert isinstance(current_request, HttpRequest) or current_request is None
    return current_request


def get_current_user() -> AbstractUser | None:
    """
    @return: current django request user object or None.
    """
    current_request = get_current_request()
    return current_request.user if current_request else None


def get_current_authenticated_user() -> AbstractUser | None:
    """
    @return: current django non-anonymous request user or None if anonymous.
    """
    current_user = get_current_user()
    if isinstance(current_user, AnonymousUser):
        return None
    return current_user


def get_current_username() -> str:
    """
    @return: username of the current non-anonymous django request user or empty string.
    """
    current_user = get_current_authenticated_user()
    return current_user.username if current_user else ''


# official pattern to extend log records: https://docs.python.org/3/library/logging.html#logging.LogRecord
__old_log_record_factory = logging.getLogRecordFactory()


def record_with_username_factory(*args, **kwargs):
    record = __old_log_record_factory(*args, **kwargs)
    record.username = get_current_username()
    return record


logging.setLogRecordFactory(record_with_username_factory)
