from typing import Optional
from django.db import models


class SemaphoreRecord(models.Model):
    key = models.CharField(max_length=512, primary_key=True, editable=False,  help_text='semaphore unique name')
    timeout = models.FloatField(help_text='interval in seconds after which the semaphore is considered open')
    pinged = models.DateTimeField(null=True, blank=True, help_text='semaphore last pinged at')
    locked = models.DateTimeField(null=True, blank=True, help_text='semaphore locked at')
    modified = models.DateTimeField(auto_now=True, editable=False, help_text='database record last modified at')

    def __str__(self):
        return self.key


class TaskHandle(models.Model):
    task_id = models.CharField('Task ID', max_length=32, editable=False)
    ormq_id = models.IntegerField(
        'OrmQ ID', null=True, blank=True, editable=False,
        help_text='Django-Q ORM message broker record ID'
    )
    cancel_requested = models.BooleanField(
        'Cancel', default=False, help_text='task cancellation requested'
    )
    created_at = models.DateTimeField(
        'Created at', auto_now_add=True, editable=False, help_text='database record created at'
    )
    updated_at = models.DateTimeField(
        'Updated at', auto_now=True, editable=False, help_text='database record last updated at'
    )

    def __str__(self):
        return f'TaskHandle(id={self.id}, task_id={self.task_id}, ormq_id={self.ormq_id if self.ormq_id else "?"})'

    @classmethod
    def get(cls, handle_or_task_id: int | str) -> Optional['TaskHandle']:
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
