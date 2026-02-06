from django.contrib import admin
from django.utils.html import format_html_join

from bats_ai.core.models import CompressedSpectrogram


@admin.register(CompressedSpectrogram)
class CompressedSpectrogramAdmin(admin.ModelAdmin):
    list_display = [
        'pk',
        'recording',
        'spectrogram',
        'length',
        'widths',
        'starts',
        'stops',
        'image_url_list_display',
        'mask_url_list_display',
    ]
    list_display_links = ['pk', 'recording', 'spectrogram']
    list_select_related = True
    autocomplete_fields = ['recording']
    readonly_fields = [
        'recording',
        'spectrogram',
        'created',
        'modified',
        'widths',
        'starts',
        'stops',
        'image_url_list_display',
        'mask_url_list_display',
    ]

    @admin.display(description='Image URLs')
    def image_url_list_display(self, obj):
        """Render each image URL as a clickable link in admin detail view."""
        urls = obj.image_url_list
        if not urls:
            return '(No images)'
        return format_html_join(
            '\n', '<div><a href="{}" target="_blank">{}</a></div>', ((url, url) for url in urls)
        )

    @admin.display(description='Mask URLs')
    def mask_url_list_display(self, obj):
        """Render each mask URL as a clickable link in admin detail view."""
        urls = obj.mask_url_list
        if not urls:
            return '(No masks)'
        return format_html_join(
            '\n', '<div><a href="{}" target="_blank">{}</a></div>', ((url, url) for url in urls)
        )
