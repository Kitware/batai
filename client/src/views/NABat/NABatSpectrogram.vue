<script lang="ts">
import {
  defineComponent,
  onMounted,
  type Ref,
  ref,
  watch,
} from "vue";
import {
  getSpecies,
  type Species,
} from "@api/api";
import {
  getNABatSpectrogram,
  getNABatSpectrogramCompressed,
} from "@api/NABatApi";
import SpectrogramViewer from "@components/SpectrogramViewer.vue";
import type { SpectroInfo } from "@components/geoJS/geoJSUtils";
import ThumbnailViewer from "@components/ThumbnailViewer.vue";
import useState from "@use/useState";
import ColorSchemeDialog from "@components/ColorSchemeDialog.vue";
import TransparencyFilterControl from "@/components/TransparencyFilterControl.vue";
import RecordingInfoDialog from "@components/RecordingInfoDialog.vue";
import RecordingAnnotations from "@components/RecordingAnnotations.vue";
import { usePrompt } from '@use/prompt-service';
import { useJWTToken } from '@use/useJWTToken';

export default defineComponent({
  name: "Spectrogram",
  components: {
    SpectrogramViewer,
    ThumbnailViewer,
    RecordingInfoDialog,
    RecordingAnnotations,
    ColorSchemeDialog,
    TransparencyFilterControl
  },
  props: {
    id: {
      type: String,
      required: true,
    },
    apiToken: {
        type: String,
        required: false,
        default: () => '',
      },
  },
  setup(props) {
    const {
      toggleLayerVisibility,
      layerVisibility,
      colorScale,
      selectedId,
      selectedType,
      scaledVals,
      viewCompressedOverlay,
      sideTab,
      configuration,
      measuring,
      toggleMeasureMode,
      drawingBoundingBox,
      toggleDrawingBoundingBox,
      fixedAxes,
      toggleFixedAxes,
    } = useState();
    const secondsWarning = 60;
    const { prompt } = usePrompt();
    const { shouldWarn, } = useJWTToken({
      'token': props.apiToken,
      'warningSeconds': secondsWarning,
    });
    const images: Ref<HTMLImageElement[]> = ref([]);
    const spectroInfo: Ref<SpectroInfo | undefined> = ref();
    const selectedUsers: Ref<string[]> = ref([]);
    const speciesList: Ref<Species[]> = ref([]);
    const loadedImage = ref(false);
    const allImagesLoaded: Ref<boolean[]> = ref([]);
    const compressed =  ref(configuration.value.spectrogram_view === 'compressed');
    const errorMessage: Ref<string | null> = ref(null);
    const additionalErrors: Ref<string[]> = ref([]);

    const gridEnabled = ref(false);
    const recordingInfo = ref(false);
    const recordingMap = ref(false);

    const disabledFeatures = ref(['speciesLabel', 'endpointLabels', 'durationLabels', 'timeLabels']);
    const loadData = async () => {
      loadedImage.value = false;
      try {
      const response = compressed.value
        ? await getNABatSpectrogramCompressed(props.id, props.apiToken)
        : await getNABatSpectrogram(props.id, props.apiToken);
      if (response.data.urls.length) {
        const urls = response.data.urls;
        images.value = [];
        allImagesLoaded.value = [];
        loadedImage.value = false;
        urls.forEach((url) => {
          const image = new Image();
          image.src = url;
          images.value.push(image);
          allImagesLoaded.value.push(false);
        });
        images.value.forEach((image, index) => {
          image.onload = () => {
            allImagesLoaded.value[index] = true;
            if (allImagesLoaded.value.every((item) => (item))) {
              loadedImage.value = true;
            }
          };
        });
      } else {
        // TODO Error Out if there is no URL
        console.error("No URL found for the spectrogram");
      }
      spectroInfo.value = response.data["spectroInfo"];
      if (response.data['compressed'] && spectroInfo.value) {
        spectroInfo.value.start_times = response.data.compressed.start_times;
        spectroInfo.value.end_times = response.data.compressed.end_times;
        viewCompressedOverlay.value = false;
      }
      const speciesResponse = await getSpecies({ recordingId: parseInt(props.id) });
      // Removing NOISE species from list and any duplicates
      speciesList.value = speciesResponse.data.filter(
        (value, index, self) => value.species_code !== "NOISE" && index === self.findIndex((t) => t.species_code === value.species_code)
      );
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (error: any) {
        errorMessage.value = `Failed fetch Spectrogram: ${error.message}:`;
        if (error.response.data.errors?.length) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          additionalErrors.value = error.response.data.errors.map((item: any) => JSON.stringify(item));
        } else if (error.response.data.error) {
          additionalErrors.value.push(error.response.data.error);
        } else {
          additionalErrors.value.push('An unknown error occurred');
        }
      }
    };
    const setSelection = (annotationId: number) => {
      selectedId.value = annotationId;
    };
    watch(gridEnabled, () => {
      toggleLayerVisibility("grid");
    });
    watch(
      () => props.id,
      () => {
        loadData();
      }
    );
    onMounted(() => {
      loadData();
    });
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
    watch(compressed, () => {
      loadData();
      if (drawingBoundingBox.value) {
        toggleDrawingBoundingBox();
      }
    });


    const toggleCompressedOverlay = () => {
      viewCompressedOverlay.value = ! viewCompressedOverlay.value;
    };

    watch(shouldWarn, async() => {
      if (shouldWarn.value && props.apiToken) {
        await prompt({
          title: 'API Token Expiration',
          text: [
          `The Api Token will expire in less than ${secondsWarning} seconds`,
          'The Refresh option will be added in the future',
          ]
        });
      }
    }, { immediate: true });

    return {
      errorMessage,
      additionalErrors,
      compressed,
      loadedImage,
      images,
      spectroInfo,
      selectedId,
      selectedType,
      setSelection,
      setParentGeoViewer,
      setHoverData,
      toggleLayerVisibility,
      speciesList,
      parentGeoViewerRef,
      gridEnabled,
      layerVisibility,
      timeRef,
      freqRef,
      toggleCompressedOverlay,
      viewCompressedOverlay,
      sideTab,
      measuring,
      toggleMeasureMode,
      drawingBoundingBox,
      toggleDrawingBoundingBox,
      fixedAxes,
      toggleFixedAxes,
      // Other user selection
      selectedUsers,
      colorScale,
      scaledVals,
      recordingInfo,
      // Disabled Featuers not in NABat
      disabledFeatures,
      recordingMap,
    };
  },
});
</script>

<template>
  <v-row
    v-if="!errorMessage"
    dense
  >
    <v-dialog
      v-model="recordingInfo"
      width="600"
    >
      <recording-info-dialog
        :id="id"
        display-mode="both"
        @close="recordingInfo = false"
      />
    </v-dialog>
    <v-dialog
      v-model="recordingMap"
      width="600"
    >
      <recording-info-dialog
        :id="id"
        display-mode="map"
        @close="recordingMap = false"
      />
    </v-dialog>
    <v-col>
      <v-toolbar>
        <v-container>
          <v-row align="center">
            <v-tooltip bottom>
              <template #activator="{ props: subProps }">
                <v-icon
                  v-bind="subProps"
                  size="40"
                  @click="recordingInfo = true"
                >
                  mdi-information-outline
                </v-icon>
              </template>
              <span> Recording Information </span>
            </v-tooltip>
            <v-tooltip bottom>
              <template #activator="{ props: subProps }">
                <v-icon
                  v-bind="subProps"
                  size="40"
                  class="ml-2"
                  @click="recordingMap = true"
                >
                  mdi-map
                </v-icon>
              </template>
              <span> Recording Location Map </span>
            </v-tooltip>

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
              v-if="scaledVals.x > 1 || scaledVals.y > 1"
              cols="2"
            >
              <div>
                <b>xScale:</b>
                <span>{{ scaledVals.x.toFixed(2) }}x</span>
              </div>
              <div>
                <b>yScale:</b>
                <span>{{ scaledVals.y.toFixed(2) }}x</span>
              </div>
            </v-col>

            <v-tooltip bottom>
              <template #activator="{ props: subProps }">
                <v-icon
                  v-bind="subProps"
                  size="40"
                  :color="compressed ? 'blue' : ''"
                  @click="compressed = !compressed"
                >
                  mdi-calendar-collapse-horizontal
                </v-icon>
              </template>
              <span> Toggle Compressed View</span>
            </v-tooltip>
            <v-spacer />
            <v-tooltip>
              <template #activator="{ props: subProps }">
                <v-icon
                  v-bind="subProps"
                  size="25"
                  class="mr-5 mt-5"
                  :color="drawingBoundingBox ? 'blue' : ''"
                  @click="toggleDrawingBoundingBox"
                >
                  mdi-border-radius
                </v-icon>
              </template>
              <span>Draw a bound box to measure pulses</span>
            </v-tooltip>
            <v-tooltip>
              <template #activator="{ props: subProps }">
                <v-icon
                  v-bind="subProps"
                  size="25"
                  class="mr-5 mt-5"
                  :color="measuring ? 'blue' : ''"
                  @click="toggleMeasureMode"
                >
                  mdi-ruler
                </v-icon>
              </template>
              <span>Use a draggable straight edge to measure frequency</span>
            </v-tooltip>
            <v-tooltip
              v-if="!disabledFeatures.includes('speciesLabel')"
              bottom
            >
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
            <v-tooltip
              v-if="!disabledFeatures.includes('endpointLabels')"
              bottom
            >
              <template #activator="{ props: subProps }">
                <v-btn
                  v-bind="subProps"
                  size="35"
                  class="mr-5 mt-5"
                  :color="layerVisibility.includes('time') ? 'blue' : ''"
                  @click="toggleLayerVisibility('time')"
                >
                  <v-icon>mdi-arrow-left-right</v-icon>
                  <h4>ms</h4>
                </v-btn>
              </template>
              <span> Turn Time Endpoint Labels On/Off</span>
            </v-tooltip>
            <v-tooltip
              v-if="!disabledFeatures.includes('durationLabels')"
              bottom
            >
              <template #activator="{ props: subProps }">
                <v-btn
                  v-bind="subProps"
                  size="35"
                  class="mr-5 mt-5"
                  :color="layerVisibility.includes('duration') ? 'blue' : ''"
                  @click="toggleLayerVisibility('duration')"
                >
                  <v-icon>mdi-arrow-expand-horizontal</v-icon>
                  <h4>ms</h4>
                </v-btn>
              </template>
              <span> Turn Time Duration Labels On/Off</span>
            </v-tooltip>
            <v-tooltip
              v-if="!disabledFeatures.includes('timeLabels')"
              bottom
            >
              <template #activator="{ props: subProps }">
                <v-btn
                  v-bind="subProps"
                  size="35"
                  class="mr-3 mt-5"
                  :color="layerVisibility.includes('freq') ? 'blue' : ''"
                  @click="toggleLayerVisibility('freq')"
                >
                  <h3>KHz</h3>
                </v-btn>
              </template>
              <span> Turn Time Label On/Off</span>
            </v-tooltip>
            <v-tooltip
              v-if="!compressed"
              bottom
            >
              <template #activator="{ props: subProps }">
                <v-icon
                  v-bind="subProps"
                  size="35"
                  class="mr-3 mt-5"
                  :color="viewCompressedOverlay ? 'blue' : ''"
                  @click="toggleCompressedOverlay()"
                >
                  mdi-format-color-highlight
                </v-icon>
              </template>
              <span> Highlight Compressed Areas</span>
            </v-tooltip>
            <div class="mr-1 mt-5">
              <transparency-filter-control />
            </div>
            <v-menu>
              <template #activator="{ props: subProps }">
                <v-btn
                  v-bind="subProps"
                  icon
                  size="25"
                  class="mr-5 mt-5"
                  variant="text"
                >
                  <v-icon>
                    mdi-cog
                  </v-icon>
                </v-btn>
              </template>
              <v-list>
                <v-list-subheader>Settings</v-list-subheader>
                <v-list-item @click="toggleFixedAxes">
                  <v-list-item-title>
                    <v-icon
                      :color="fixedAxes ? 'blue' : ''"
                    >
                      {{ fixedAxes ? 'mdi-axis-lock' : 'mdi-axis' }}
                    </v-icon>
                    <span>
                      Toggle Axes Type
                    </span>
                  </v-list-item-title>
                </v-list-item>
                <v-list-item @click="gridEnabled = !gridEnabled">
                  <v-list-item-title>
                    <v-icon
                      :color="gridEnabled ? 'blue' : ''"
                    >
                      {{ gridEnabled ? 'mdi-grid' : 'mdi-grid-off' }}
                    </v-icon>
                    <span>
                      Toggle Grid
                    </span>
                  </v-list-item-title>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>
                    <ColorSchemeDialog display-mode="menu" />
                  </v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
          </v-row>
        </v-container>
      </v-toolbar>
      <spectrogram-viewer
        v-if="loadedImage && spectroInfo"
        :images="images"
        :spectro-info="spectroInfo"
        :recording-id="id"
        :grid="gridEnabled"
        :compressed="compressed"
        class="spectro-main"
        @selected="setSelection($event)"
        @geo-viewer-ref="setParentGeoViewer($event)"
        @hover-data="setHoverData($event)"
      />
      <thumbnail-viewer
        v-if="loadedImage && parentGeoViewerRef"
        :images="images"
        :spectro-info="spectroInfo"
        :recording-id="id"
        :parent-geo-viewer-ref="parentGeoViewerRef"
        @selected="setSelection($event)"
      />
    </v-col>
    <v-col style="max-width: 400px">
      <v-card>
        <v-card-title>
          <v-row dense>
            <v-col cols="2">
              <v-spacer />
            </v-col>
            <v-col cols="4">
              <v-tooltip bottom>
                <template #activator="{ props: subProps }">
                  <v-btn
                    v-bind="subProps"
                    :variant="sideTab === 'annotations' ? 'flat' : 'outlined'"
                    :color="sideTab === 'annotations' ? 'primary' : ''"
                    class="mx-2"
                    size="small"
                    @click="sideTab = 'annotations'"
                  >
                    Annotations
                  </v-btn>
                </template>
                <span>
                  View Annotations in sideTab
                </span>
              </v-tooltip>
            </v-col>
            <v-col>
              <v-spacer />
            </v-col>
          </v-row>
        </v-card-title>
        <v-card-text class="pa-0">
          <div
            v-if="sideTab === 'annotations' && speciesList.length"
          >
            <RecordingAnnotations
              :species="speciesList"
              :recording-id="parseInt(id)"
              :api-token="apiToken"
              type="nabat"
            />
          </div>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
  <v-alert
    v-if="errorMessage"
    type="error"
  >
    {{ errorMessage }}
    <div v-if="additionalErrors.length">
      <ul>
        <li
          v-for="(error, index) in additionalErrors"
          :key="index"
        >
          {{ error }}
        </li>
      </ul>
    </div>
  </v-alert>
</template>

<style scoped>
.spectro-main {
  height: calc(100vh - 21vh - 64px - 72px);
}
.color-scheme-flex {
  display:flex;
  align-items: center;
}
</style>
