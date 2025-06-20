from rest_framework import mixins, serializers, viewsets

from bats_ai.core.models.nabat import NABatCompressedSpectrogram


class NABatCompressedSpectrogramSerializer(serializers.ModelSerializer):
    class Meta:
        model = NABatCompressedSpectrogram
        fields = '__all__'


class NaBatCompressedSpectrogramViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = NABatCompressedSpectrogram.objects.all()
    serializer_class = NABatCompressedSpectrogramSerializer

    FILE_FIELD_NAME = 'image_file'
