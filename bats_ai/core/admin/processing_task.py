from django.contrib import admin

from bats_ai.core.models import ProcessingTask


@admin.register(ProcessingTask)
class ProcessingTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'status', 'created', 'modified', 'celery_id', 'metadata', 'error')
    list_filter = ('status', 'created', 'modified')
    search_fields = ('name', 'celery_id', 'metadata', 'error')
    ordering = ('-created',)
    readonly_fields = ('created', 'modified')
    fieldsets = (
        (None, {'fields': ('name', 'status', 'celery_id', 'error')}),
        (
            'Metadata',
            {
                'classes': ('collapse',),
                'fields': ('metadata',),
            },
        ),
        (
            'Timestamps',
            {
                'fields': ('created', 'modified'),
            },
        ),
    )
