import logging
from django.contrib import admin
from django.utils.html import format_html

# local imports
from .models import SemaphoreRecord, TaskHandle, LogEntry


DB_LOG_ENTRY_ADMIN_LIST_PER_PAGE = 30


@admin.register(SemaphoreRecord)
class SemaphoreRecordAdmin(admin.ModelAdmin):
    list_display = ['key', 'timeout', 'pinged', 'locked', 'modified']


@admin.register(TaskHandle)
class TaskHandleAdmin(admin.ModelAdmin):
    list_display = ['id', 'task_id', 'ormq_id', 'cancel_requested', 'created_at', 'updated_at']


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('colored_msg', 'traceback', 'created_at_format')
    list_display_links = ('colored_msg', )
    list_filter = ('level', )
    list_per_page = DB_LOG_ENTRY_ADMIN_LIST_PER_PAGE

    def colored_msg(self, instance):
        if instance.level in [logging.NOTSET, logging.INFO]:
            color = 'green'
        elif instance.level in [logging.WARNING, logging.DEBUG]:
            color = 'orange'
        else:
            color = 'red'
        return format_html('<span style="color: {color};">{msg}</span>', color=color, msg=instance.msg)
    colored_msg.short_description = 'Message'

    @staticmethod
    def traceback(instance):
        return format_html('<pre><code>{content}</code></pre>', content=instance.trace if instance.trace else '')

    def created_at_format(self, instance):
        return instance.created_at.strftime('%Y-%m-%d %X')
    created_at_format.short_description = 'Created at'
