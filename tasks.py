import functools
import logging
from django.db import transaction
from django.dispatch import receiver
from django_q.tasks import async_task
from django_q.signals import pre_execute

# local imports
from .models import TaskHandle

log = logging.getLogger(__name__)


def queue_task(func, *args, **kwargs) -> TaskHandle:
    with transaction.atomic():
        task_id = async_task(func, *args, **kwargs)
        task_handle = TaskHandle(task_id=task_id)
        task_handle.save()
        return task_handle


CURRENT_TASK_ID_ATTR_NAME = '__current_task_id'


@receiver(pre_execute)
def django_q_pre_execute_callback(sender, func, task, **kwargs):
    _, _, _ = sender, func, kwargs
    task_id = getattr(django_q_pre_execute_callback, CURRENT_TASK_ID_ATTR_NAME, None)
    if task_id:
        raise RuntimeError(f'current_task_id already set to "{task_id}"')
    task_id = task["id"]
    log.info(f'pre_execute: task_id={task_id}')
    setattr(django_q_pre_execute_callback, CURRENT_TASK_ID_ATTR_NAME, task_id)


def current_task_id(_func: callable = None):
    def decorator(func: callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            task_id = getattr(django_q_pre_execute_callback, CURRENT_TASK_ID_ATTR_NAME)
            try:
                return func(*args, **kwargs, task_id=task_id)
            finally:
                actual_task_id = getattr(django_q_pre_execute_callback, CURRENT_TASK_ID_ATTR_NAME)
                if actual_task_id != task_id:
                    raise RuntimeError(f'incorrect task id: {actual_task_id}, expected: {task_id}')
                delattr(django_q_pre_execute_callback, CURRENT_TASK_ID_ATTR_NAME)

        return wrapper

    if _func is None:
        return decorator
    else:
        return decorator(_func)
