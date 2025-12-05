from django.contrib import admin

from bats_ai.core.models import ComputedPulseAnnotation


@admin.register(ComputedPulseAnnotation)
class ComputedPulseAnnotationAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'recording',
        'bounding_box',
    ]
    list_select_related = True
