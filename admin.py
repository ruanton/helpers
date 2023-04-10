import logging
from django.contrib import admin
from django.utils.html import format_html

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

    def colored_description(self, instance):
        if instance.level in [logging.NOTSET, logging.INFO]:
            color = 'green'
        elif instance.level in [logging.WARNING, logging.DEBUG]:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {color};">{msg}</span>',
            color=color,
            msg=f'{instance.created_at.astimezone().strftime("%Y-%m-%d %X")} {instance.name} — {instance.msg}'
        )
    colored_description.short_description = 'Message with info'

    @staticmethod
    def traceback(instance):
        return format_html('<pre><code>{content}</code></pre>', content=instance.trace if instance.trace else '')
