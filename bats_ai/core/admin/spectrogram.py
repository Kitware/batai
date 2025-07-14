from django.contrib import admin
from django.utils.html import format_html_join

from bats_ai.core.models import Spectrogram


@admin.register(Spectrogram)
class SpectrogramAdmin(admin.ModelAdmin):
    list_display = [
        'pk',
        'recording',
        'width',
        'height',
        'duration',
        'frequency_min',
        'frequency_max',
        'image_url_list_display',
    ]
    list_display_links = ['pk', 'recording']
    list_select_related = True
    autocomplete_fields = ['recording']
    readonly_fields = [
        'recording',
        'created',
        'modified',
        'width',
        'height',
        'duration',
        'frequency_min',
        'frequency_max',
        'image_url_list_display',
    ]

    @admin.display(description='Image URLs')
    def image_url_list_display(self, obj):
        """Show image URLs as clickable links in both detail and list views."""
        urls = obj.image_url_list
        if not urls:
            return '(No images)'
        return format_html_join(
            '\n', '<div><a href="{}" target="_blank">{}</a></div>', ((url, url) for url in urls)
        )
