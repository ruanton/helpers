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


class TaskInfo:
    def __init__(self, task_dict: dict):
        self.task_dict: dict = task_dict
        self.handle = TaskHandle.objects.get(task_id=task_dict['id'])
        self._history: list[TaskHandle] = []

        # save ID of Django-Q ORM queue item
        ormq_id = task_dict['ack_id'] if 'ack_id' in task_dict else None
        if ormq_id:
            if (self.handle.ormq_id or '') != ormq_id:
                if self.handle.ormq_id:
                    log.warning(f'ormq_id already set to: "{self.handle.ormq_id}", changing to "{ormq_id}"')
                self.handle.ormq_id = ormq_id
                self.handle.save()
        else:
            log.warning('no "ack_id" attribute in task info dictionary')

    @property
    def history(self) -> list[TaskHandle]:
        if not self._history:
            handle = self.handle
            while handle:
                # verify consistency
                if handle.prev:
                    if handle.try_num != handle.prev.try_num + 1:
                        log.warning(f'inconsistent try number for task handle {handle.id}: {handle.try_num}')
                    if handle.max_tries != handle.prev.max_tries:
                        log.warning(f'inconsistent max_tries for task handle {handle.id}: {handle.max_tries}')
                elif handle.try_num != 1:
                    log.warning(f'inconsistent try number for task handle {handle.id}: {handle.try_num}')

                self._history.append(handle)
                handle = handle.prev

        return self._history

    @property
    def cancel_requested(self) -> bool:
        return any(x.cancel_requested for x in self.history)

    @property
    def is_last_try(self) -> bool:
        return self.handle.try_num >= self.handle.max_tries


def async_task_with_handle(func, *args, prev: TaskHandle = None, tries: int = None, **kwargs) -> TaskHandle:
    """
    Creates asynchronous task for executing by Django Q cluster by calling async_task.
    Additionally, creates database record with handle to control this task and it's retries.
    @param func: the task function
    @param prev: task handle of the previous try
    @param tries: maximum number of retries in case of failure
    @param args: positional arguments of the task function
    @param kwargs: keyword arguments of the task function
    @return: TaskHandle object created
    """
    if prev and tries:
        raise ValueError('prev and tries cannot be given simultaneously')
    if not tries and not prev:
        tries = 1

    with transaction.atomic():
        task_id = async_task(func, *args, **kwargs)
        if tries:
            task_handle = TaskHandle(task_id=task_id, max_tries=tries)
            task_handle.save()
        else:
            task_handle = TaskHandle(task_id=task_id, prev=prev, max_tries=prev.max_tries, try_num=prev.try_num + 1)
            prev.next = task_handle
            task_handle.save()
            prev.save()
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
        existing_task_info: TaskInfo = getattr(django_q_pre_execute_callback, CURRENT_TASK_INFO_ATTR_NAME, None)
        if existing_task_info:
            raise RuntimeError(
                f'{CURRENT_TASK_INFO_ATTR_NAME} already set to "... task_id={existing_task_info.handle.task_id} ...", '
                f'forgot to use "current_task_info" decorator?'
            )
        log.debug(f'pre_execute: task_id={task["id"]}')
        task_info = TaskInfo(task_dict=task)
        setattr(django_q_pre_execute_callback, CURRENT_TASK_INFO_ATTR_NAME, task_info)  # save the task info globally


def current_task_info(_func: callable = None):
    """
    This decorator gives task info to function and clears the task info global attribute on exit. Must be outermost.
    """
    def decorator(func: callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            task_info: TaskInfo = getattr(django_q_pre_execute_callback, CURRENT_TASK_INFO_ATTR_NAME)
            try:
                return func(*args, **kwargs, task_info=task_info)
            finally:
                actual_task_info: TaskInfo = getattr(django_q_pre_execute_callback, CURRENT_TASK_INFO_ATTR_NAME)
                if actual_task_info != task_info:
                    raise RuntimeError(
                        f'incorrect task id: {actual_task_info.handle.task_id}, expected: {task_info.handle.task_id}')
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
    task_info: TaskInfo = getattr(django_q_pre_execute_callback, CURRENT_TASK_INFO_ATTR_NAME, None)
    record.task_id = task_info.handle.task_id if task_info else ''
    return record


logging.setLogRecordFactory(record_with_task_id_factory)
