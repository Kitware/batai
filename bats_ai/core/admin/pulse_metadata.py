from django.contrib import admin

from bats_ai.core.models import PulseMetadata


@admin.register(PulseMetadata)
class PulseMetadataAdmin(admin.ModelAdmin):
    list_display = ('recording', 'index', 'bounding_box')
    list_select_related = True
