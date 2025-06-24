from django.contrib import admin

from bats_ai.core.models import ExportedAnnotationFile


@admin.register(ExportedAnnotationFile)
class ExportedAnnotationFileAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'file',
        'download_url',
        'status',
        'expires_at',
        'created',
        'modified',
    )
    list_filter = ('status', 'created', 'modified', 'expires_at')
    search_fields = ('download_url', 'file')
    ordering = ('-created',)
    readonly_fields = ('created', 'modified')

    fieldsets = (
        (None, {'fields': ('file', 'download_url', 'status', 'expires_at')}),
        (
            'Filters Applied',
            {
                'classes': ('collapse',),
                'fields': ('filters_applied',),
            },
        ),
        (
            'Timestamps',
            {
                'fields': ('created', 'modified'),
            },
        ),
    )
