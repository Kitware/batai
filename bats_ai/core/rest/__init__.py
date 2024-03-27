from rest_framework import routers

from .image import ImageViewSet
from .spectrogram import SpectrogramViewSet

__all__ = ['ImageViewSet', 'SpectrogramViewSet']

rest = routers.SimpleRouter()
# rest.register(r'images', ImageViewSet)
rest.register(r'spectrograms', SpectrogramViewSet)
