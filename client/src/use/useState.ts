import { ref, Ref, watch } from "vue";
import { useRouter } from 'vue-router';
import { cloneDeep } from "lodash";
import * as d3 from "d3";
import {
  Configuration,
  getConfiguration,
  getCurrentUser,
  OtherUserAnnotations,
  Recording,
  SpectrogramAnnotation,
  SpectrogramSequenceAnnotation,
  RecordingTag,
} from "../api/api";
import {
  interpolateCividis,
  interpolateViridis,
  interpolateInferno,
  interpolateMagma,
  interpolatePlasma,
  interpolateTurbo,
} from "d3-scale-chromatic";

const annotationState: Ref<AnnotationState> = ref("");
const creationType: Ref<"pulse" | "sequence"> = ref("pulse");
type LayersVis = "time" | "freq" | "species" | "grid" | "sequence" | "duration";
const layerVisibility: Ref<LayersVis[]> = ref(["sequence", "species", "duration", "freq"]);
const colorScale: Ref<d3.ScaleOrdinal<string, string, never> | undefined> = ref();
const colorSchemes = [
  { value: "inferno", title: "Inferno", scheme: interpolateInferno },
  { value: "cividis", title: "Cividis", scheme: interpolateCividis },
  { value: "viridis", title: "Viridis", scheme: interpolateViridis },
  { value: "magma", title: "Magma", scheme: interpolateMagma },
  { value: "plasma", title: "Plasma", scheme: interpolatePlasma },
  { value: "turbo", title: "Turbo", scheme: interpolateTurbo },
];
const colorScheme: Ref<{ value: string; title: string; scheme: (input: number) => string }> = ref(
  colorSchemes[0]
);
const backgroundColor = ref("rgb(0, 0, 0)");
const selectedUsers: Ref<string[]> = ref([]);
const currentUser: Ref<string> = ref("");
const selectedId: Ref<number | null> = ref(null);
const selectedType: Ref<"pulse" | "sequence"> = ref("pulse");
const annotations: Ref<SpectrogramAnnotation[]> = ref([]);
const sequenceAnnotations: Ref<SpectrogramSequenceAnnotation[]> = ref([]);
const otherUserAnnotations: Ref<OtherUserAnnotations> = ref({});
const sharedList: Ref<Recording[]> = ref([]);
const recordingList: Ref<Recording[]> = ref([]);
const recordingTagList: Ref<RecordingTag[]> = ref([]);
const nextShared: Ref<Recording | false> = ref(false);
const scaledVals: Ref<{ x: number; y: number }> = ref({ x: 1, y: 1 });
const viewCompressedOverlay = ref(false);
const sideTab: Ref<"annotations" | "recordings"> = ref("annotations");
const configuration: Ref<Configuration> = ref({
  display_pulse_annotations: true,
  display_sequence_annotations: true,
  spectrogram_view: "compressed",
  spectrogram_x_stretch: 2.5,
  run_inference_on_upload: true,
  default_color_scheme: "inferno",
  default_spectrogram_background_color: "rgb(0, 0, 0)",
  is_admin: false,
  mark_annotations_completed_enabled: false,
  non_admin_upload_enabled: true,
  show_my_recordings: true,
});
const scaledWidth = ref(0);
const scaledHeight = ref(0);
const measuring: Ref<boolean> = ref(false);
const frequencyRulerY: Ref<number> = ref(0);
const toggleMeasureMode = () => {
  measuring.value = !measuring.value;
};
const drawingBoundingBox = ref(false);
const boundingBoxError = ref('');
const toggleDrawingBoundingBox = () => {
  drawingBoundingBox.value = !drawingBoundingBox.value;
};

const fixedAxes = ref(true);
const toggleFixedAxes = () => {
  fixedAxes.value = !fixedAxes.value;
};

type AnnotationState = "" | "editing" | "creating" | "disabled";
export default function useState() {
  const setAnnotationState = (state: AnnotationState) => {
    annotationState.value = state;
  };
  function toggleLayerVisibility(value: LayersVis) {
    const index = layerVisibility.value.indexOf(value);
    const clone = cloneDeep(layerVisibility.value);
    if (index === -1) {
      // If the value is not present, add it
      clone.push(value);
    } else {
      // If the value is present, remove it
      clone.splice(index, 1);
    }
    if (value === "time" && clone.includes("duration")) {
      const durationInd = layerVisibility.value.indexOf("duration");
      clone.splice(durationInd, 1);
    }
    if (value === "duration" && clone.includes("time")) {
      const timeInd = layerVisibility.value.indexOf("time");
      clone.splice(timeInd, 1);
    }
    layerVisibility.value = clone;
  }
  const setSelectedUsers = (newUsers: string[]) => {
    selectedUsers.value = newUsers;
  };

  function createColorScale(userEmails: string[]) {
    colorScale.value = d3
      .scaleOrdinal<string>()
      .domain(userEmails)
      .range(
        d3.schemeCategory10.filter(
          (color) => color !== "red" && color !== "cyan" && color !== "yellow"
        )
      );
  }

  function setSelectedId(id: number | null, annotationType?: "pulse" | "sequence") {
    selectedId.value = id;
    if (annotationType) {
      selectedType.value = annotationType;
    }
  }
  watch(sharedList, () => {
    const filtered = sharedList.value.filter((item) => !item.userMadeAnnotations);
    if (filtered.length > 0) {
      nextShared.value = filtered[0];
    } else {
      nextShared.value = false;
    }
  });

  async function loadConfiguration() {
    configuration.value = (await getConfiguration()).data;
  }

  async function loadCurrentUser() {
    const userInfo = (await getCurrentUser()).data;
    currentUser.value = userInfo.name;
  }

  /**
   * Function used to determine whether or not we are currently looking
   * at an NABat-specific view.
   *
   * returns `true` if looking at an NABat view, `false` otherwise
   */
  function isNaBat(): boolean {
    const router = useRouter();
    return router.currentRoute.value.fullPath.includes('nabat');
  }


  return {
    annotationState,
    creationType,
    setAnnotationState,
    toggleLayerVisibility,
    layerVisibility,
    createColorScale,
    colorScale,
    measuring,
    toggleMeasureMode,
    frequencyRulerY,
    drawingBoundingBox,
    boundingBoxError,
    toggleDrawingBoundingBox,
    colorSchemes,
    colorScheme,
    backgroundColor,
    setSelectedUsers,
    selectedUsers,
    currentUser,
    setSelectedId,
    loadConfiguration,
    loadCurrentUser,
    isNaBat,
    // State Passing Elements
    annotations,
    configuration,
    sequenceAnnotations,
    otherUserAnnotations,
    selectedId,
    selectedType,
    sharedList,
    recordingList,
    recordingTagList,
    nextShared,
    scaledVals,
    viewCompressedOverlay,
    sideTab,
    scaledWidth,
    scaledHeight,
    fixedAxes,
    toggleFixedAxes,
  };
}
