from django.contrib import admin

from bats_ai.core.models.configuration import Configuration


@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        'display_pulse_annotations',
        'display_sequence_annotations',
        'run_inference_on_upload',
        'spectrogram_x_stretch',
        'spectrogram_view',
    )

    def has_add_permission(self, request):
        # Allow add only if there is no Configuration instance
        if Configuration.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        # Prevent deleting the Configuration through the admin
        return False
