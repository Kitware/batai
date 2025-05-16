<script lang="ts">
import {
  defineComponent,
  onMounted,
  Ref,
  ref,
  watch,
} from "vue";
import {
  getSpecies,
  Species,
} from "@api/api";
import {
  getNABatSpectrogram,
  getNABatSpectrogramCompressed,
} from "@api/NABatApi";
import SpectrogramViewer from "@components/SpectrogramViewer.vue";
import { SpectroInfo } from "@components/geoJS/geoJSUtils";
import ThumbnailViewer from "@components/ThumbnailViewer.vue";
import useState from "@use/useState";
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
  },
  props: {
    id: {
      type: String,
      required: true,
    },
    apiToken: {
        type: String,
        required: true,
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
    } = useState();
    const secondsWarning = 60;
    const { prompt } = usePrompt();
    const { shouldWarn, } = useJWTToken({
      'token': props.apiToken,
      'warningSeconds': secondsWarning,
    });
    const image: Ref<HTMLImageElement> = ref(new Image());
    const spectroInfo: Ref<SpectroInfo | undefined> = ref();
    const selectedUsers: Ref<string[]> = ref([]);
    const speciesList: Ref<Species[]> = ref([]);
    const loadedImage = ref(false);
    const compressed =  ref(configuration.value.spectrogram_view === 'compressed');
    const errorMessage: Ref<string | null> = ref(null);
    const additionalErrors: Ref<string[]> = ref([]);

    const gridEnabled = ref(false);
    const recordingInfo = ref(false);

    const disabledFeatures = ref(['speciesLabel', 'endpointLabels', 'durationLabels', 'timeLabels']);
    const loadData = async () => {
      loadedImage.value = false;
      try {
      const response = compressed.value
        ? await getNABatSpectrogramCompressed(props.id, props.apiToken)
        : await getNABatSpectrogram(props.id, props.apiToken);
      if (response.data["url"]) {
        if (import.meta.env.PROD) {
        const updateHost = `${window.location.protocol}//${window.location.hostname}/`;
        const updatedURL = response.data["url"].replace(
          "http://127.0.0.1:9000/",
          updateHost
        );
        image.value.src = updatedURL.split("?")[0];
        } else {
          image.value.src = response.data['url'];
        }
      } else {
        // TODO Error Out if there is no URL
        console.error("No URL found for the spectrogram");
      }
      image.value.onload = () => {
        loadedImage.value = true;
      };
      spectroInfo.value = response.data["spectroInfo"];
      if (response.data['compressed'] && spectroInfo.value) {
        spectroInfo.value.start_times = response.data.compressed.start_times;
        spectroInfo.value.end_times = response.data.compressed.end_times;
        viewCompressedOverlay.value = false;
      }
      const speciesResponse = await getSpecies();
      speciesList.value = speciesResponse.data;
    } catch (error) {
        errorMessage.value = `Failed fetch Spectrogram: ${error.message}:`;
        if (error.response.data.errors?.length) {
          additionalErrors.value = error.response.data.errors.map((item) => JSON.stringify(item));
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


    const toggleCompressedOverlay = () => {
      viewCompressedOverlay.value = ! viewCompressedOverlay.value;
    };

    watch(shouldWarn, async() => {
      if (shouldWarn.value) {
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
      image,
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
      // Other user selection
      selectedUsers,
      colorScale,
      scaledVals,
      recordingInfo,
      // Disabled Featuers not in NABat
      disabledFeatures,
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
        @close="recordingInfo = false"
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
                <span v-if="timeRef >= 0">{{ scaledVals.x.toFixed(2) }}x</span>
              </div>
              <div>
                <b>yScale:</b>
                <span v-if="freqRef >= 0">{{ scaledVals.y.toFixed(2) }}x</span>
              </div>
            </v-col>
            <v-spacer />
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
            <v-tooltip
              v-if="!compressed"
              bottom
            >
              <template #activator="{ props: subProps }">
                <v-icon
                  v-bind="subProps"
                  size="35"
                  class="mr-5 mt-5"
                  :color="viewCompressedOverlay ? 'blue' : ''"
                  @click="toggleCompressedOverlay()"
                >
                  mdi-format-color-highlight
                </v-icon>
              </template>
              <span> Highlight Compressed Areas</span>
            </v-tooltip>
          </v-row>
        </v-container>
      </v-toolbar>
      <spectrogram-viewer
        v-if="loadedImage && spectroInfo"
        :image="image"
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
        :image="image"
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
            <v-spacer />
            <v-tooltip
              bottom
            >
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
            <v-spacer />
          </v-row>
        </v-card-title>
        <v-card-text class="pa-0">
          <div v-if="sideTab === 'annotations'">
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
</style>
