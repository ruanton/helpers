from django.contrib import admin

# local imports
from .models import SemaphoreRecord, TaskHandle


@admin.register(SemaphoreRecord)
class SemaphoreRecordAdmin(admin.ModelAdmin):
    list_display = ['key', 'timeout', 'pinged', 'locked', 'modified']


@admin.register(TaskHandle)
class TaskHandleAdmin(admin.ModelAdmin):
    list_display = ['id', 'task_id', 'ormq_id', 'cancel_requested', 'created_at', 'updated_at']
