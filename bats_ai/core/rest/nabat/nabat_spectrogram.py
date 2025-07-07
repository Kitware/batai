from rest_framework import mixins, serializers, viewsets

from bats_ai.core.models.nabat import NABatSpectrogram


class NABatSpectrogramSerializer(serializers.ModelSerializer):
    class Meta:
        model = NABatSpectrogram
        fields = '__all__'


class NABatSpectrogramViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = NABatSpectrogram.objects.all()
    serializer_class = NABatSpectrogramSerializer
