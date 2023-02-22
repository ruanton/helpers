from django.db import models


class SemaphoreRecord(models.Model):
    key = models.CharField('Semaphore unique name', max_length=512, primary_key=True)
    timeout = models.FloatField('Interval in seconds after which the semaphore is considered open')
    pinged = models.DateTimeField('Last pinged at', null=True, blank=True)
    locked = models.DateTimeField('Semaphore locked at', null=True, blank=True)
    modified = models.DateTimeField('Record modified at', auto_now=True)

    def __str__(self):
        return self.key
