from rest_framework import routers

from .spectrogram import SpectrogramViewSet

__all__ = ['SpectrogramViewSet']

rest = routers.SimpleRouter()
rest.register(r'spectrograms', SpectrogramViewSet)
