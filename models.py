from django.db import models


class SemaphoreRecord(models.Model):
    key = models.CharField('Semaphore unique name', max_length=512, primary_key=True)
    timeout = models.FloatField('Interval in seconds after which the semaphore is considered open')
    pinged = models.DateTimeField('Last pinged at', null=True, blank=True)
    locked = models.DateTimeField('Semaphore locked at', null=True, blank=True)
    modified = models.DateTimeField('Record modified at', auto_now=True)

    def __str__(self):
        return self.key


class TaskHandle(models.Model):
    task_id = models.CharField('Task ID', max_length=32)
    ormq_id = models.IntegerField('Queue record ID', null=True, blank=True)
    cancel_requested = models.BooleanField('Task cancellation requested', default=False)
    created_at = models.DateTimeField('Created at', auto_now_add=True, editable=False)
    updated_at = models.DateTimeField('Updated at', auto_now=True, editable=False)

    class Meta:
        # indexes = [
        #     models.Index(fields=['task_id'], name='idx_task_handle_task_id')
        # ]
        constraints = [
            models.UniqueConstraint(fields=['task_id'], name='uniq_task_handle_task_id')
        ]
