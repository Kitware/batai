<script lang="ts">
import { computed, defineComponent, onMounted, Ref, ref, } from 'vue';
import { getSpecies, getAnnotations, getSpectrogram, Species, SpectrogramAnnotation, getSpectrogramCompressed } from '../api/api';
import SpectrogramViewer from '../components/SpectrogramViewer.vue';
import { SpectroInfo } from '../components/geoJS/geoJSUtils';
import AnnotationList from '../components/AnnotationList.vue';
import AnnotationEditor from '../components/AnnotationEditor.vue';
import ThumbnailViewer from '../components/ThumbnailViewer.vue';
import { watch } from 'vue';

export default defineComponent({
  name: "Spectrogram",
  components: {
    SpectrogramViewer,
    AnnotationList,
    AnnotationEditor,
    ThumbnailViewer,
  },
  props: {
    id: {
      type: String,
      required: true,
    },
  },
  setup(props) {
    const image: Ref<HTMLImageElement> = ref(new Image());
    const spectroInfo: Ref<SpectroInfo | undefined> = ref();
    const annotations: Ref<SpectrogramAnnotation[] | undefined> = ref([]);
    const selectedId: Ref<number | null> = ref(null);
    const speciesList: Ref<Species[]> = ref([]);
    const loadedImage = ref(false);
    const compressed = ref(false);
    const getAnnotationsList= async (annotationId?: number) => {
        const response = await getAnnotations(props.id);
        annotations.value = response.data;
        if (annotationId !== undefined) {
          selectedId.value = annotationId;
        }
        
    };
    const loadData = async () => {
      loadedImage.value = false;
      const response = compressed.value ? await getSpectrogramCompressed(props.id) : await getSpectrogram(props.id);
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
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const parentGeoViewerRef: Ref<any> = ref(null);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const setParentGeoViewer = (data: any) => {
      parentGeoViewerRef.value = data;

    };
    watch(compressed, () => loadData());
    return { 
      compressed,
      loadedImage,
      image,
      spectroInfo,
      annotations,
      selectedId,
      setSelection,
      getAnnotationsList,
      setParentGeoViewer,
      speciesList,
      selectedAnnotation,
      parentGeoViewerRef,
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
        @geo-viewer-ref="setParentGeoViewer($event)"
      />
      <thumbnail-viewer
        v-if="loadedImage && parentGeoViewerRef"
        :image="image"
        :spectro-info="spectroInfo"
        :recording-id="id"
        :annotations="annotations"
        :selected-id="selectedId"
        :parent-geo-viewer-ref="parentGeoViewerRef"
        @selected="setSelection($event)"
      />
    </v-col>
    <v-col style="max-width:300px">
      <v-switch
        v-model="compressed"
        label="Compressed"
        density="compact"
        class="ma-0 pa-0"
      />
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
