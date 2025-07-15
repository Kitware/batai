from rest_framework import mixins, serializers, viewsets

from bats_ai.core.models import Spectrogram


class SpectrogramSerializer(serializers.ModelSerializer):
    class Meta:
        model = Spectrogram
        fields = '__all__'


class SpectrogramViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Spectrogram.objects.all()
    serializer_class = SpectrogramSerializer
