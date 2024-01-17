<script lang="ts">
import { computed, defineComponent, onMounted, Ref, ref, } from 'vue';
import { getSpecies, getAnnotations, getSpectrogram, Species, SpectrogramAnnotation } from '../api/api';
import SpectrogramViewer from '../components/SpectrogramViewer.vue';
import { SpectroInfo } from '../components/geoJS/geoJSUtils';
import AnnotationList from '../components/AnnotationList.vue';
import AnnotationEditor from '../components/AnnotationEditor.vue';

export default defineComponent({
  name: "Spectrogram",
  components: {
    SpectrogramViewer,
    AnnotationList,
    AnnotationEditor,
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
    const selectedId: Ref<number | null> = ref(null);
    const speciesList: Ref<Species[]> = ref([]);
    const loadedImage = ref(false);
    const getAnnotationsList= async (annotationId?: number) => {
        const response = await getAnnotations(props.id);
        annotations.value = response.data;
        if (annotationId !== undefined) {
          selectedId.value = annotationId;
        }
        
    };
    const loadData = async () => {
      const response = await getSpectrogram(props.id);
      image.value.src = `data:image/png;base64,${response.data['base64_spectrogram']}`;
      spectroInfo.value = response.data['spectroInfo'];
      annotations.value = response.data['annotations'];
      loadedImage.value = true;
      const speciesResponse = await getSpecies();
      speciesList.value = speciesResponse.data;
    };
    const setSelection = (annotationId: number) => {
      selectedId.value= annotationId;
    };
    const selectedAnnotation = computed(() => {
      if (selectedId.value !== null && annotations.value) {
        const found = annotations.value.findIndex((item) => item.id === selectedId.value);
          if (found !== -1) {
            return annotations.value[found];
          }
        }
      return null;
    });
    onMounted(() => loadData());
    return { 
      loadedImage,
      image,
      spectroInfo,
      annotations,
      selectedId,
      setSelection,
      getAnnotationsList,
      speciesList,
      selectedAnnotation,
    };
  },
});
</script>

<template>
  <v-row>
    <v-col>
      <spectrogram-viewer
        v-if="loadedImage"
        :image="image"
        :spectro-info="spectroInfo"
        :recording-id="id"
        :annotations="annotations"
        :selected-id="selectedId"
        @selected="setSelection($event)"
        @create:annotation="getAnnotationsList($event)"
      />
    </v-col>
    <v-col style="max-width:300px">
      <annotation-list
        :annotations="annotations"
        :selected-id="selectedId"
        @select="selectedId = $event"
      />
      <annotation-editor
        v-if="selectedAnnotation"
        :species="speciesList"
        :recording-id="id"
        :annotation="selectedAnnotation"
        class="mt-4"
        @update:annotation="getAnnotationsList()"
        @delete:annotation="getAnnotationsList()"
      />
    </v-col>
  </v-row>
</template>
