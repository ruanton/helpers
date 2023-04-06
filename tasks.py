import functools
import logging
from django.db import transaction
from django.dispatch import receiver
from django.conf import settings
from django_q.tasks import async_task
from django_q.signals import pre_execute

# local imports
from .models import TaskHandle

log = logging.getLogger(__name__)


def async_task_with_handle(func, *args, **kwargs) -> TaskHandle:
    """
    Creates asynchronous task for executing by Django Q cluster by calling async_task.
    Additionally, creates database record with handle to control this task.
    @param func: the task function
    @param args: positional arguments of the task function
    @param kwargs: keyword arguments of the task function
    @return: TaskHandle object created
    """
    with transaction.atomic():
        task_id = async_task(func, *args, **kwargs)
        task_handle = TaskHandle(task_id=task_id)
        task_handle.save()
        return task_handle


CURRENT_TASK_INFO_ATTR_NAME = '__current_task_info'


@receiver(pre_execute)
def django_q_pre_execute_callback(sender, func, task, **kwargs):
    """
    Saves task info globally. Turned on by settings.CURRENT_TASK_INFO_TRACKING = True.
    If turned on, requires clearing the global attribute after each task execution (use current_task_info decorator).
    """
    _, _, _ = sender, func, kwargs
    if getattr(settings, 'CURRENT_TASK_INFO_TRACKING', None):
        existing_task_info = getattr(django_q_pre_execute_callback, CURRENT_TASK_INFO_ATTR_NAME, None)
        if existing_task_info:
            raise RuntimeError(
                f'{CURRENT_TASK_INFO_ATTR_NAME} already set to "... task_id={existing_task_info["id"]} ...", '
                f'forgot to use "current_task_info" decorator?'
            )
        log.info(f'pre_execute: task_id={task["id"]}')
        setattr(django_q_pre_execute_callback, CURRENT_TASK_INFO_ATTR_NAME, task)  # save the task info globally


def current_task_info(_func: callable = None):
    """
    This decorator gives task info to function and clears the task info global attribute on exit. Must be outermost.
    """
    def decorator(func: callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            task_info = getattr(django_q_pre_execute_callback, CURRENT_TASK_INFO_ATTR_NAME)
            try:
                return func(*args, **kwargs, task=task_info)
            finally:
                actual_task_info = getattr(django_q_pre_execute_callback, CURRENT_TASK_INFO_ATTR_NAME)
                if actual_task_info['id'] != task_info['id']:
                    raise RuntimeError(f'incorrect task id: {actual_task_info["id"]}, expected: {task_info["id"]}')
                delattr(django_q_pre_execute_callback, CURRENT_TASK_INFO_ATTR_NAME)

        return wrapper

    if _func is None:
        return decorator
    else:
        return decorator(_func)


# official pattern to extend log records: https://docs.python.org/3/library/logging.html#logging.LogRecord
__old_log_record_factory = logging.getLogRecordFactory()


def record_with_task_id_factory(*args, **kwargs):
    record = __old_log_record_factory(*args, **kwargs)
    task_info = getattr(django_q_pre_execute_callback, CURRENT_TASK_INFO_ATTR_NAME, None)
    record.task_id = task_info['id'] if task_info else None
    return record


logging.setLogRecordFactory(record_with_task_id_factory)
