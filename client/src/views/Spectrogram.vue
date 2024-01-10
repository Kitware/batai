<script lang="ts">
import { defineComponent, onMounted, Ref, ref, } from 'vue';
import { getSpectrogram, SpectrogramAnnotation } from '../api/api';
import SpectrogramViewer from '../components/SpectrogramViewer.vue';
import { SpectroInfo } from '../components/geoJS/geoJSUtils';

export default defineComponent({
  name: "Spectrogram",
  components: {
    SpectrogramViewer,
  },
  props: {
    id: {
      type: String,
      required: true,
    }
  },
  setup(props) {
    const image: Ref<HTMLImageElement> = ref(new Image());
    const spectroInfo: Ref<SpectroInfo | undefined> = ref();
    const annotations: Ref<SpectrogramAnnotation[] | undefined> = ref([]);
    const loadedImage = ref(false);
    const loadData = async () => {
      const response = await getSpectrogram(props.id);
      image.value.src = `data:image/png;base64,${response.data['base64_spectrogram']}`;
      spectroInfo.value = response.data['spectroInfo'];
      annotations.value = response.data['annotations'];
      loadedImage.value = true;
    };
    onMounted(() => loadData());
    return { 
      loadedImage,
      image,
      spectroInfo,
      annotations,
    };
  },
});
</script>

<template>
  <spectrogram-viewer
    v-if="loadedImage"
    :image="image"
    :spectro-info="spectroInfo"
    :annotations="annotations"
  />
</template>
