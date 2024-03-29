import logging
from typing import Optional
from django.db import models
from django.utils.html import format_html


class DeferManager(models.Manager):
    """
    Defers database loading from certain fields.

    Usage in Models classes:
        objects = DeferManager('field_name', ...)
    """
    def __init__(self, *fields: str):
        super(DeferManager, self).__init__()
        self.fields_to_defer = fields

    def get_queryset(self):
        return super(DeferManager, self).get_queryset().defer(*self.fields_to_defer)


class SemaphoreRecord(models.Model):
    key = models.CharField(max_length=512, primary_key=True, editable=False,  help_text='semaphore unique name')
    timeout = models.FloatField(help_text='interval in seconds after which the semaphore is considered open')
    pinged = models.DateTimeField(null=True, blank=True, help_text='semaphore last pinged at')
    locked = models.DateTimeField(null=True, blank=True, help_text='semaphore locked at')
    modified = models.DateTimeField(auto_now=True, editable=False, help_text='database record last modified at')

    def __str__(self):
        return self.key


class TaskHandle(models.Model):
    task_id = models.CharField('Task ID', max_length=32, editable=False);  """Django-Q task unique ID."""
    ormq_id = models.IntegerField(
        'OrmQ ID', null=True, blank=True, editable=False,
        help_text='Django-Q ORM message broker record ID'
    )
    """Unique ID of the record in Django-Q ormq table."""

    cancel_requested = models.BooleanField('Cancel', default=False, help_text='task cancellation requested')
    """Flag for cancellation. Running tasks supposed to check this flag and gratefully terminate as soon as possible."""

    prev = models.ForeignKey(
        to='self', on_delete=models.CASCADE, related_name='next_handle', null=True, blank=True, editable=False,
        help_text='handle of the previous task try'
    )
    """Task Handle of the previous task try if it was failed."""

    next = models.ForeignKey(
        to='self', on_delete=models.CASCADE, related_name='prev_handle', null=True, blank=True, editable=False,
        help_text='handle of the next task try'
    )
    """Task Handle of the next task try. Created in case of failure of this task."""

    max_tries = models.IntegerField(default=1, help_text='max number of tries', editable=False)
    """Set to identical value for all Task Handles in the retry chain."""

    try_num = models.IntegerField(default=1, help_text='try number', editable=False)
    """Try number in the retrying chain. Counts from 1."""

    created_at = models.DateTimeField('Created at', auto_now_add=True, editable=False, help_text='db record created at')
    updated_at = models.DateTimeField('Updated at', auto_now=True, editable=False, help_text='db record updated at')

    def __str__(self):
        return f'TaskHandle(id={self.id}, task_id={self.task_id}, ormq_id={self.ormq_id if self.ormq_id else "?"})'

    @classmethod
    def get(cls, handle_or_task_id: int | str) -> Optional['TaskHandle']:
        """Get Task Handle by ID or task_id. Returns None if not found."""
        if TaskHandle.objects.filter(id=handle_or_task_id).exists():
            return TaskHandle.objects.get(id=handle_or_task_id)
        elif TaskHandle.objects.filter(task_id=handle_or_task_id).exists():
            return TaskHandle.objects.get(task_id=handle_or_task_id)
        else:
            return None

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['task_id'], name='uniq_task_handle_task_id')
        ]


LOG_LEVELS = (
    (logging.NOTSET, 'NotSet'),
    (logging.INFO, 'Info'),
    (logging.WARNING, 'Warning'),
    (logging.DEBUG, 'Debug'),
    (logging.ERROR, 'Error'),
    (logging.FATAL, 'Fatal'),
)


class LogEntry(models.Model):
    name = models.CharField('Logger name', max_length=100)
    level = models.PositiveSmallIntegerField(choices=LOG_LEVELS, default=logging.ERROR)
    msg = models.TextField()
    trace = models.TextField(blank=True)
    task_id = models.CharField('Task ID', max_length=32, blank=True, editable=False)
    username = models.CharField(max_length=150, blank=True, editable=False)
    created_at = models.DateTimeField('Created at', auto_now_add=True, help_text='db record created at')

    def __str__(self):
        return self.msg

    def colored_description(self):
        if self.level in [logging.NOTSET, logging.INFO]:
            color = 'green'
        elif self.level in [logging.WARNING, logging.DEBUG]:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {color};">{msg}</span>',
            color=color,
            msg=f'[{self.created_at.astimezone().strftime("%Y-%m-%d %X")}] {self.name} — {self.msg}'
        )
    colored_description.short_description = 'Message with info'

    def colored_description_short(self):
        if self.level in [logging.NOTSET, logging.INFO]:
            color = 'green'
        elif self.level in [logging.WARNING, logging.DEBUG]:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {color};">{msg}</span>',
            color=color,
            msg=f'[{self.created_at.astimezone().strftime("%Y-%m-%d %X")}] - {self.msg}'
        )
    colored_description_short.short_description = 'Message with info'

    def traceback(self):
        return format_html('<pre><code>{content}</code></pre>', content=self.trace if self.trace else '')

    def level_name(self):
        return logging.getLevelName(self.level)

    class Meta:
        ordering = ('-created_at', )
        verbose_name_plural = 'Log entries'

        indexes = [
            models.Index(fields=['level', '-created_at'], name='idx_log_entry_level'),
            models.Index(fields=['task_id', '-created_at'], name='idx_log_entry_task_id'),
        ]
