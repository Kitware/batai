from django.contrib import admin

from bats_ai.core.models import SpectrogramSvg


@admin.register(SpectrogramSvg)
class SpectrogramSvgAdmin(admin.ModelAdmin):
    list_display = [
        'pk',
        'content_type',
        'object_id',
        'index',
        'image_file',
    ]
    list_select_related = True
    readonly_fields = [
        'pk',
        'content_type',
        'object_id',
        'index',
        'image_file',
    ]
