from django.contrib import admin

# local imports
from .models import SemaphoreRecord, TaskHandle, LogEntry


DB_LOG_ENTRY_ADMIN_LIST_PER_PAGE = 200


@admin.register(SemaphoreRecord)
class SemaphoreRecordAdmin(admin.ModelAdmin):
    list_display = ['key', 'timeout', 'pinged', 'locked', 'modified']


@admin.register(TaskHandle)
class TaskHandleAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'task_id', 'ormq_id', '_prev', '_next', '_try', 'cancel_requested', '_created', '_updated'
    ]

    @admin.display(description='Prev')
    def _prev(self, obj):
        return obj.prev_id

    @admin.display(description='Next')
    def _next(self, obj):
        return obj.next_id

    @admin.display(description='Try')
    def _try(self, obj):
        return obj.try_num

    @admin.display(description='Created at')
    def _created(self, obj):
        return f'{obj.created_at.astimezone():%Y-%m-%d %X}'

    @admin.display(description='Updates at')
    def _updated(self, obj):
        return f'{obj.updated_at.astimezone():%Y-%m-%d %X}'


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('colored_description', )
    list_display_links = ('colored_description', )
    list_filter = ('level', )
    list_per_page = DB_LOG_ENTRY_ADMIN_LIST_PER_PAGE
