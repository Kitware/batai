<script lang="ts">
import { defineComponent, onMounted, Ref, ref, } from 'vue';
import { getSpectrogram } from '../api/api';
import SpectrogramViewer from '../components/SpectrogramViewer.vue';

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
    const loadedImage = ref(false);
    const loadData = async () => {
      const response = await getSpectrogram(props.id);
      image.value.src = `data:image/png;base64,${response.data['base64_spectrogram']}`;
      
      loadedImage.value = true;
    };
    onMounted(() => loadData());
    return { 
      loadedImage,
      image,
    };
  },
});
</script>

<template>
  <spectrogram-viewer
    v-if="loadedImage"
    :image="image"
  />
</template>
