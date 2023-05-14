import functools
import logging
import threading
from django.db import transaction
from django.dispatch import receiver
from django.conf import settings
from django_q.tasks import async_task
from django_q.signals import pre_execute

# local imports
from .models import TaskHandle

log = logging.getLogger(__name__)

_thread_locals = threading.local()
CURRENT_TASK_INFO_ATTR_NAME = '__current_task_info'
"""Attribute name for saving Task Info of the current Django-Q task into _thead_locals."""


class TaskInfo:
    """Information of the currently running Django-Q task."""
    def __init__(self, task_dict: dict):
        # retrieve task handle record from the database
        task_id = task_dict['id']
        try:
            task_handle = TaskHandle.objects.get(task_id=task_id)
        except TaskHandle.DoesNotExist:
            raise RuntimeError(
                f'TaskHandle record with task_id={task_id} does not exists, '
                f'forgot to always use "async_task_with_handle()" to queue task?'
            )

        # save ID of Django-Q ORM queue item
        ormq_id = task_dict['ack_id'] if 'ack_id' in task_dict else None
        if ormq_id:
            if (task_handle.ormq_id or '') != ormq_id:
                """If OrmQ ID not in database yet, save it."""
                if task_handle.ormq_id:
                    log.warning(f'ormq_id already set to: "{task_handle.ormq_id}", changing to "{ormq_id}"')
                task_handle.ormq_id = ormq_id
                task_handle.save()
        else:
            log.warning('no "ack_id" attribute in task info dictionary')

        self.task_dict: dict = task_dict;  """Dictionary passed to Django-Q pre_execute callback handler."""
        self.handle = task_handle;  """Task Handle"""
        self._history: list[TaskHandle] = [];  """List of Task Handles of the retry chain."""

    def __str__(self):
        handle_id = self.handle.id
        task_id = self.handle.task_id
        ormq_id = self.handle.ormq_id or 'unknown'
        return f'handle_id={handle_id}, task_id={task_id}, ormq_id={ormq_id}'

    @property
    def history(self) -> list[TaskHandle]:
        """Task Handles of the retry chain, reversed. Cached on the first request."""
        if not self._history:
            handle = self.handle
            while handle:
                # verify consistency
                if handle.prev:
                    if handle.try_num != handle.prev.try_num + 1:
                        # try_num's for Task Handles in the retry chain must follow each other
                        log.warning(f'inconsistent try number for task handle {handle.id}: {handle.try_num}')
                    if handle.max_tries != handle.prev.max_tries:
                        # all max_tries of Task Handles of the retry chain must be identical
                        log.warning(f'inconsistent max_tries for task handle {handle.id}: {handle.max_tries}')
                elif handle.try_num != 1:
                    # try_num of the first Task Handle must be set to 1
                    log.warning(f'inconsistent try number for task handle {handle.id}: {handle.try_num}')

                self._history.append(handle)
                handle = handle.prev

        return self._history

    @property
    def cancel_requested(self) -> bool:
        """Returns True if task cancellation is requested through any of the Task Handles of the retry chain."""
        return any(x.cancel_requested for x in self.history)

    @property
    def is_last_try(self) -> bool:
        """Returns True if this task is the last try according to given max_tries."""
        return self.handle.try_num >= self.handle.max_tries


def async_task_with_handle(func, *args, prev: TaskHandle = None, tries: int = None, **kwargs) -> TaskHandle:
    """
    Creates asynchronous task for executing by Django-Q cluster, by calling async_task.
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
        # by default only one try is requested
        tries = 1

    with transaction.atomic():
        task_id = async_task(func, *args, **kwargs)  # queue Django-Q task for execution
        if tries:
            # this is the first try of the task
            task_handle = TaskHandle(task_id=task_id, max_tries=tries)  # create Task Handle database record
            task_handle.save()
        else:
            # this is the following try of the (failed) task
            task_handle = TaskHandle(task_id=task_id, prev=prev, max_tries=prev.max_tries, try_num=prev.try_num + 1)
            prev.next = task_handle  # chain created Task Handle to the previous tries list
            task_handle.save()
            prev.save()
        return task_handle


@receiver(pre_execute)
def django_q_pre_execute_callback(sender, func, task, **kwargs):
    """
    Saves task info globally (in the current thread).
    Turned on by settings.CURRENT_TASK_INFO_TRACKING = True.
    If turned on, requires clearing the global attribute after each task execution (use '@managed_task' decorator).
    Supposed that only one Django-Q task can be run on any particular thread.
    """
    _, _, _ = sender, func, kwargs  # suppress PyCharm warning about unused params
    if getattr(settings, 'CURRENT_TASK_INFO_TRACKING', None):
        existing_task_info: TaskInfo = getattr(_thread_locals, CURRENT_TASK_INFO_ATTR_NAME, None)
        if existing_task_info:
            raise RuntimeError(
                f'{CURRENT_TASK_INFO_ATTR_NAME} already set to "... task_id={existing_task_info.handle.task_id} ...", '
                f'forgot to use "@managed_task" decorator?'
            )
        log.info(f'pre_execute: task_id={task["id"]}')
        task_info = TaskInfo(task_dict=task)
        setattr(_thread_locals, CURRENT_TASK_INFO_ATTR_NAME, task_info)  # save the task info globally


def managed_task(_func: callable = None):
    """
    This decorator turns a task function to a managed Django-Q task:
       • gives TaskInfo to this function as task_info additional attribute;
       • clears the task_info global (in the current thread) attribute on exit;
       • automatically manages required task retries;
       • automatically skips task execution if next task try is already queued;
       • automatically skips task execution if task cancellation is requested;

    Supposed that such Django-Q async tasks always created with 'async_task_with_handle' function
    for TaskHandle DB record to be created.

    Requires settings.CURRENT_TASK_INFO_ATTR_NAME set to True.

    Must be outermost decorator.
    """
    def decorator(func: callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # retrieve current task information, previously saved via pre_execute Django-Q handler
            task_info: TaskInfo = getattr(_thread_locals, CURRENT_TASK_INFO_ATTR_NAME)
            if not task_info:
                raise RuntimeError('no task_info, forgot to to set settings.CURRENT_TASK_INFO_TRACKING=True?')

            try:
                if task_info.handle.next:
                    log.warning(f'next task already queued: {task_info.handle.next.task_id}, terminating')
                    return 'the next task try is already queued, skipping'
                if task_info.cancel_requested:
                    log.info('task cancellation requested, terminating')
                    return 'task cancellation is requested, skipping task execution'

                log.info(f'running task: {task_info}')
                return func(*args, **kwargs, task_info=task_info)

            except Exception:
                if task_info.is_last_try:
                    log.info(f'task failed permanently: {task_info}', exc_info=True)
                else:
                    # queue task retry if not last try
                    next_task_handle = async_task_with_handle(func, *args, prev=task_info.handle, **kwargs)
                    log.info(f'task try failed: {task_info}, next try {next_task_handle.try_num} queued', exc_info=True)

                # propagate exception to be saved in Django-Q scheduler database table of failed tasks
                raise

            finally:
                # verify the task info in the _thread_locals is not changed during task execution
                actual_task_info: TaskInfo = getattr(_thread_locals, CURRENT_TASK_INFO_ATTR_NAME)
                actual_task_id = actual_task_info.handle.task_id
                expected_task_id = task_info.handle.task_id
                if actual_task_info != task_info:
                    raise RuntimeError(f'incorrect task id: {actual_task_id}, expected: {expected_task_id}')

                # always clear correctly saved task_info attribute on exit
                delattr(_thread_locals, CURRENT_TASK_INFO_ATTR_NAME)

        return wrapper

    if _func is None:
        return decorator
    else:
        return decorator(_func)


# official pattern to extend log records: https://docs.python.org/3/library/logging.html#logging.LogRecord
__old_log_record_factory = logging.getLogRecordFactory()


def record_with_task_id_factory(*args, **kwargs):
    """Adds task_id attribute to every log record. If no task_id - sets attribute to empty string."""
    record = __old_log_record_factory(*args, **kwargs)
    task_info: TaskInfo = getattr(_thread_locals, CURRENT_TASK_INFO_ATTR_NAME, None)
    record.task_id = task_info.handle.task_id if task_info else ''
    return record


logging.setLogRecordFactory(record_with_task_id_factory)
