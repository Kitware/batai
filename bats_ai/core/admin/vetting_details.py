from __future__ import annotations

from django.contrib import admin

from bats_ai.core.models import VettingDetails


@admin.register(VettingDetails)
class VettingDetailsAdmin(admin.ModelAdmin):
    list_display = [
        'pk',
        'user',
        # 'reference_materials',
    ]
    search_fields = ('user',)
