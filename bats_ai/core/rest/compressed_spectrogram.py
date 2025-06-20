from rest_framework import mixins, serializers, viewsets

from bats_ai.core.models import CompressedSpectrogram


class CompressedSpectrogramSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompressedSpectrogram
        fields = '__all__'


class CompressedSpectrogramViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = CompressedSpectrogram.objects.all()
    serializer_class = CompressedSpectrogramSerializer
