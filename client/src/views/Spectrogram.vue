<script lang="ts">
import { computed, defineComponent, onMounted, onUnmounted, Ref, ref } from "vue";
import {
  getSpecies,
  getAnnotations,
  getSpectrogram,
  Species,
  SpectrogramAnnotation,
  getSpectrogramCompressed,
} from "../api/api";
import SpectrogramViewer from "../components/SpectrogramViewer.vue";
import { SpectroInfo } from "../components/geoJS/geoJSUtils";
import AnnotationList from "../components/AnnotationList.vue";
import AnnotationEditor from "../components/AnnotationEditor.vue";
import ThumbnailViewer from "../components/ThumbnailViewer.vue";
import { watch } from "vue";
import useState from "../use/useState";
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
    const { toggleLayerVisibility, layerVisibility } = useState();
    const image: Ref<HTMLImageElement> = ref(new Image());
    const spectroInfo: Ref<SpectroInfo | undefined> = ref();
    const annotations: Ref<SpectrogramAnnotation[] | undefined> = ref([]);
    const selectedId: Ref<number | null> = ref(null);
    const speciesList: Ref<Species[]> = ref([]);
    const loadedImage = ref(false);
    const compressed = ref(false);
    const gridEnabled = ref(false);
    const mode: Ref<"creation" | "editing" | "disabled"> = ref("disabled");
    const getAnnotationsList = async (annotationId?: number) => {
      const response = await getAnnotations(props.id);
      annotations.value = response.data.sort((a, b) => a.start_time - b.start_time);
      if (annotationId !== undefined) {
        selectedId.value = annotationId;
      }
    };
    const selectedIndex = computed(() => {
      if (annotations.value && selectedId.value !== null) {
        return annotations.value.findIndex((item) => item.id === selectedId.value);
      }
      return -1;
    });
    const selectNextIndex = (dir: -1 | 1) => {
      if (annotations.value && annotations.value.length) {
        const newIndex = selectedIndex.value + dir;
        if (newIndex < 0) {
          selectedId.value = annotations.value[annotations.value.length - 1].id;
        } else if (newIndex > annotations.value.length - 1) {
          selectedId.value = annotations.value[0].id;
        } else {
          selectedId.value = annotations.value[newIndex].id;
        }
      }
    };

    const loadData = async () => {
      loadedImage.value = false;
      const response = compressed.value
        ? await getSpectrogramCompressed(props.id)
        : await getSpectrogram(props.id);
      image.value.src = `data:image/png;base64,${response.data["base64_spectrogram"]}`;
      spectroInfo.value = response.data["spectroInfo"];
      annotations.value = response.data["annotations"]?.sort((a, b) => a.start_time - b.start_time);
      loadedImage.value = true;
      const speciesResponse = await getSpecies();
      speciesList.value = speciesResponse.data;
    };
    const setSelection = (annotationId: number) => {
      selectedId.value = annotationId;
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
    watch(gridEnabled, () => {
      toggleLayerVisibility('grid');
    });
    onMounted(() => loadData());
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const parentGeoViewerRef: Ref<any> = ref(null);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const setParentGeoViewer = (data: any) => {
      parentGeoViewerRef.value = data;
    };

    const timeRef = ref(0);
    const freqRef = ref(0);
    const setHoverData = ({ time, freq }: { time: number; freq: number }) => {
      timeRef.value = time;
      freqRef.value = freq;
    };
    watch(compressed, () => loadData());

    const setMode = (newMode: "creation" | "editing" | "disabled") => {
      mode.value = newMode;
    };

    const keyboardEvent = (e: KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        selectNextIndex(1);
      } else if (e.key === "ArrowUp") {
        selectNextIndex(-1);
      }
    };
    onMounted(() => {
      window.addEventListener("keydown", keyboardEvent);
    });
    onUnmounted(() => {
      window.removeEventListener("keydown", keyboardEvent);
    });
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
      setHoverData,
      setMode,
      toggleLayerVisibility,
      speciesList,
      selectedAnnotation,
      parentGeoViewerRef,
      gridEnabled,
      layerVisibility,
      timeRef,
      freqRef,
      mode,
    };
  },
});
</script>

<template>
  <v-row>
    <v-col>
      <v-toolbar>
        <v-row>
          <v-col cols="2">
            <div>
              <b>Time:</b>
              <span v-if="timeRef >= 0">{{ timeRef.toFixed(0) }}ms</span>
            </div>
            <div>
              <b>Frequency:</b>
              <span v-if="freqRef >= 0">{{ freqRef.toFixed(2) }}KHz</span>
            </div>
          </v-col>
          <v-col
            v-if="mode !== 'disabled'"
            cols="1"
            style="font-size: 20px"
          >
            <b>Mode:</b>
            <span> {{ mode }}</span>
          </v-col>
          <v-spacer />
          <v-tooltip bottom>
            <template #activator="{ props: subProps }">
              <v-icon
                v-bind="subProps"
                size="35"
                class="mr-5 mt-5"
                :color="layerVisibility.includes('species') ? 'blue' : ''"
                @click="toggleLayerVisibility('species')"
              >
                mdi-bat
              </v-icon>
            </template>
            <span> Turn Species Label On/Off</span>
          </v-tooltip>
          <v-tooltip bottom>
            <template #activator="{ props: subProps }">
              <v-btn
                v-bind="subProps"
                size="35"
                class="mr-5 mt-5"
                :color="layerVisibility.includes('time') ? 'blue' : ''"
                @click="toggleLayerVisibility('time')"
              >
                <h3>ms</h3>
              </v-btn>
            </template>
            <span> Turn Time Label On/Off</span>
          </v-tooltip>
          <v-tooltip bottom>
            <template #activator="{ props: subProps }">
              <v-btn
                v-bind="subProps"
                size="35"
                class="mr-5 mt-5"
                :color="layerVisibility.includes('freq') ? 'blue' : ''"
                @click="toggleLayerVisibility('freq')"
              >
                <h3>KHz</h3>
              </v-btn>
            </template>
            <span> Turn Time Label On/Off</span>
          </v-tooltip>
          <v-tooltip bottom>
            <template #activator="{ props: subProps }">
              <v-icon
                v-bind="subProps"
                size="35"
                class="mr-5 mt-5"
                :color="gridEnabled ? 'blue' : ''"
                @click="gridEnabled = !gridEnabled"
              >
                mdi-grid
              </v-icon>
            </template>
            <span> Turn Legend Grid On/Off</span>
          </v-tooltip>
          <v-tooltip bottom>
            <template #activator="{ props: subProps }">
              <v-icon
                v-bind="subProps"
                size="35"
                class="mr-5 mt-5"
                :color="compressed ? 'blue' : ''"
                @click="compressed = !compressed"
              >
                mdi-calendar-collapse-horizontal
              </v-icon>
            </template>
            <span> Toggle Compressed View</span>
          </v-tooltip>
        </v-row>
      </v-toolbar>
      <spectrogram-viewer
        v-if="loadedImage"
        :image="image"
        :spectro-info="spectroInfo"
        :recording-id="id"
        :annotations="annotations"
        :selected-id="selectedId"
        :grid="gridEnabled"
        @selected="setSelection($event)"
        @create:annotation="getAnnotationsList($event)"
        @update:annotation="getAnnotationsList()"
        @geo-viewer-ref="setParentGeoViewer($event)"
        @hover-data="setHoverData($event)"
        @set-mode="setMode($event)"
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
    <v-col style="max-width: 300px">
      <annotation-list
        :annotations="annotations"
        :selected-id="selectedId"
        :mode="mode"
        class="annotation-list"
        @select="selectedId = $event"
      />
      <annotation-editor
        v-if="selectedAnnotation"
        :species="speciesList"
        :recording-id="id"
        :annotation="selectedAnnotation"
        class="mt-4"
        @update:annotation="getAnnotationsList()"
        @delete:annotation="
          getAnnotationsList();
          selectedId = null;
        "
      />
    </v-col>
  </v-row>
</template>

<style scoped>
.annotation-list {
  max-height: 60vh;
  overflow-y: auto;
}
</style>
