from rest_framework import routers

from .nabat_compressed_spectrogram import NaBatCompressedSpectrogramViewSet
from .nabat_spectrogram import NABatSpectrogramViewSet

__all__ = [
    'SpectrogramViewSet',
    'CompressedSpectrogramViewSet',
]

rest = routers.SimpleRouter()
rest.register(r'nabat/spectrograms', NABatSpectrogramViewSet)
rest.register(r'nabat/compressed_spectrograms', NaBatCompressedSpectrogramViewSet)
