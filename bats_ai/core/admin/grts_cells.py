from __future__ import annotations

from django.contrib import admin

from bats_ai.core.models import GRTSCells


@admin.register(GRTSCells)
class GRTSCellsAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'grts_cell_id',
        'sample_frame_id',
    )  # Add other fields you want to display in the list
    search_fields = ('id', 'grts_cell_id', 'sample_frame_id')  # Add fields for searching
