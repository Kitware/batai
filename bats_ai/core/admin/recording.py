from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib import admin, messages
from django.db.models import Prefetch
from django.urls import reverse
from django.utils.html import format_html

from bats_ai.core.models import CompressedSpectrogram, Recording, Spectrogram
from bats_ai.core.tasks.tasks import recording_compute_spectrogram

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest


@admin.register(Recording)
class RecordingAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "audio_file",
        "spectrogram_status",
        "compressed_spectrogram_status",
        "owner",
        "recorded_date",
        "recorded_time",
        "public",
        "equipment",
        "comments",
        "recording_location",
        "grts_cell_id",
        "sample_frame_id",
        "site_name",
        "detector",
        "software",
        "species_list",
        "unusual_occurrences",
        "get_computed_species",
        "get_official_species",
    ]
    list_select_related = ["owner"]

    search_fields = ["name"]
    actions = ["compute_spectrograms"]

    autocomplete_fields = ["owner"]
    readonly_fields = ["created", "modified"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                Prefetch(
                    "spectrograms",
                    # Ordering must be applied here, or else the prefetch cache won't be used
                    queryset=Spectrogram.objects.order_by("-created"),
                ),
                Prefetch(
                    "compressed_spectrograms",
                    # Exclude large ArrayField
                    queryset=CompressedSpectrogram.objects.defer(
                        "starts", "stops", "widths"
                    ).order_by("-created"),
                ),
                "official_species",
                "computed_species",
            )
        )

    @admin.display(
        description="Spectrogram",
        empty_value="Not computed",
    )
    def spectrogram_status(self, recording: Recording):
        if recording.spectrograms.exists():
            # Only this syntax will use the prefetch cache
            spectrogram = recording.spectrograms.all()[0]
            href = reverse("admin:core_spectrogram_change", args=(spectrogram.pk,))
            spectrogram_obj_id_str = str(spectrogram)
            return format_html('<a href="{}">{}</a>', href, spectrogram_obj_id_str)
        return None

    @admin.display(
        description="Compressed Spectrogram",
        empty_value="Not computed",
    )
    def compressed_spectrogram_status(self, recording: Recording):
        if recording.compressed_spectrograms.exists():
            # Only this syntax will use the prefetch cache
            compressed_spectrogram = recording.compressed_spectrograms.all()[0]
            href = reverse(
                "admin:core_compressedspectrogram_change", args=(compressed_spectrogram.pk,)
            )
            compressed_spectrogram_obj_id_str = str(compressed_spectrogram)
            return format_html('<a href="{}">{}</a>', href, compressed_spectrogram_obj_id_str)
        return None

    @admin.display(description="Official Species")
    def get_official_species(self, recording: Recording) -> list[str]:
        return [species.species_code_6 for species in recording.official_species.all()]

    @admin.display(description="Computed Species")
    def get_computed_species(self, recording: Recording) -> list[str]:
        return [species.species_code_6 for species in recording.computed_species.all()]

    @admin.action(description="Compute Spectrograms")
    def compute_spectrograms(self, request: HttpRequest, queryset: QuerySet):
        counter = 0
        for recording in queryset:
            recording_compute_spectrogram.delay(recording.pk)
            counter += 1
        self.message_user(request, f"{counter} recordings queued", messages.SUCCESS)
