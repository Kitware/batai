import { computed, ref, Ref, watch } from "vue";
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
  FileAnnotation,
  getComputedPulseContour,
  ComputedPulseContour,
  getVettingDetailsForUser,
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
const currentUserId: Ref<number | undefined> = ref(undefined);
const selectedId: Ref<number | null> = ref(null);
const selectedType: Ref<"pulse" | "sequence"> = ref("pulse");
const annotations: Ref<SpectrogramAnnotation[]> = ref([]);
const sequenceAnnotations: Ref<SpectrogramSequenceAnnotation[]> = ref([]);
const otherUserAnnotations: Ref<OtherUserAnnotations> = ref({});
const sharedList: Ref<Recording[]> = ref([]);
const recordingList: Ref<Recording[]> = ref([]);
const currentRecordingId: Ref<number | undefined> = ref(undefined);
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

const computedPulseContours: Ref<ComputedPulseContour[]> = ref([]);
// Initial contour state is off; not persisted or loaded from localStorage.
const contoursEnabled = ref(false);
const imageOpacity = ref(1.0);
const contourOpacity = ref(1.0);
const contoursLoading = ref(false);
const viewMaskOverlay = ref(false);
const maskOverlayOpacity = ref(0.50);
const setContoursEnabled = (value: boolean) => {
  contoursEnabled.value = value;
};
async function loadContours(recordingId: number) {
  contoursLoading.value = true;
  computedPulseContours.value = await getComputedPulseContour(recordingId);
  contoursLoading.value = false;
}
function clearContours() {
  computedPulseContours.value = [];
}

const reviewerMaterials = ref('');

const transparencyThreshold = ref(0); // 0-100 percentage

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
    currentUserId.value = userInfo.id;
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

  const showSubmittedRecordings = ref(false);

  const submittedMyRecordings = computed(() => {
    const submittedByMe = recordingList.value.filter((recording: Recording) => {
      const myAnnotations = recording.fileAnnotations.filter((annotation: FileAnnotation) => (
        annotation.owner === currentUser.value && annotation.submitted
      ));
      return myAnnotations.length > 0;
    });
    return submittedByMe;
  });

  const submittedSharedRecordings = computed(() => {
    const submittedByMe = sharedList.value.filter((recording: Recording) => {
      const myAnnotations = recording.fileAnnotations.filter((annotation: FileAnnotation) => (
        annotation.owner === currentUser.value && annotation.submitted
      ));
      return myAnnotations.length > 0;
    });
    return submittedByMe;
  });

  const unsubmittedMyRecordings = computed(() => {
    const unsubmitted = recordingList.value.filter((recording: Recording) => {
      const myAnnotations = recording.fileAnnotations.filter((annotation: FileAnnotation) => (
        annotation.owner === currentUser.value && annotation.submitted
      ));
      return myAnnotations.length === 0;
    });
    return unsubmitted;
  });

  const unsubmittedSharedRecordings = computed(() => {
    const unsubmitted = sharedList.value.filter((recording: Recording) => {
      const myAnnotations = recording.fileAnnotations.filter((annotation: FileAnnotation) => (
        annotation.owner === currentUser.value && annotation.submitted
      ));
      return myAnnotations.length === 0;
    });
    return unsubmitted;
  });

  // Use state to determine which recordings should be shown to the user
  const myRecordingsDisplay = computed(() => {
    if (!configuration.value.mark_annotations_completed_enabled) {
      return recordingList.value;
    } else {
      return showSubmittedRecordings.value ? recordingList.value : unsubmittedMyRecordings.value;
    }
  });

  const sharedRecordingsDisplay = computed(() => {
    if (!configuration.value.mark_annotations_completed_enabled) {
      return sharedList.value;
    } else {
      return showSubmittedRecordings.value ? sharedList.value : unsubmittedSharedRecordings.value;
    }
  });

  function hasSubmittedAnnotation(recording: Recording): boolean {
    return recording.fileAnnotations.some((annotation: FileAnnotation) => (
      annotation.owner === currentUser.value && annotation.submitted
    ));
  }

  const allRecordings = computed(() => {
    const recordings = recordingList.value.concat(sharedList.value);
    return recordings.map((recording: Recording) => {
      const isSubmitted = recording.fileAnnotations.some((annotation: FileAnnotation) => (
        annotation.owner === currentUser.value && annotation.submitted
      ));
      return {
        ...recording,
        submitted: isSubmitted,
      };
    });
  });

  function markAnnotationSubmitted(recordingId: number, annotationId: number) {
    const recording = allRecordings.value.find((recording: Recording) => recording.id === recordingId);
    if (!recording) return;
    const annotation = recording.fileAnnotations.find((annotation: FileAnnotation) => annotation.id === annotationId);
    if (!annotation) return;
    annotation.submitted = true;
  }

  const nextUnsubmittedRecordingId = computed(() => {
    if (allRecordings.value.length === 0) {
      return undefined;
    }
    const startingIndex = allRecordings.value.findIndex((recording: Recording) => recording.id === currentRecordingId.value) || 0;

    for (let i = startingIndex + 1; i < allRecordings.value.length; i++) {
      if (!hasSubmittedAnnotation(allRecordings.value[i])) {
        return allRecordings.value[i].id;
      }
    }

    for (let i = 0; i < startingIndex; i++) {
      if (!hasSubmittedAnnotation(allRecordings.value[i])) {
        return allRecordings.value[i].id;
      }
    }

    return undefined;
  });

  const previousUnsubmittedRecordingId = computed(() =>{
    if (allRecordings.value.length === 0) {
      return undefined;
    }
    const startingIndex = allRecordings.value.findIndex((recording: Recording) => recording.id === currentRecordingId.value) || 0;

    for (let i = startingIndex -1; i >= 0; i--) {
      if (!hasSubmittedAnnotation(allRecordings.value[i])) {
        return allRecordings.value[i].id;
      }
    }

    for (let i = allRecordings.value.length - 1; i > startingIndex; i--) {
      if (!hasSubmittedAnnotation(allRecordings.value[i])) {
        return allRecordings.value[i].id;
      }
    }

    return undefined;
  });

  async function loadReviewerMaterials() {
    // Only make this request if vetting is enabled and a user is logged in
    if (!configuration.value.mark_annotations_completed_enabled) return;
    if (currentUserId.value === undefined) return;

    const vettingDetails = await getVettingDetailsForUser(currentUserId.value);
    if (vettingDetails) {
      reviewerMaterials.value = vettingDetails.reference_materials;
    }
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
    currentUserId,
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
    transparencyThreshold,
    contoursEnabled,
    imageOpacity,
    contourOpacity,
    contoursLoading,
    setContoursEnabled,
    loadContours,
    clearContours,
    computedPulseContours,
    showSubmittedRecordings,
    submittedMyRecordings,
    submittedSharedRecordings,
    unsubmittedMyRecordings,
    unsubmittedSharedRecordings,
    myRecordingsDisplay,
    sharedRecordingsDisplay,
    nextUnsubmittedRecordingId,
    previousUnsubmittedRecordingId,
    markAnnotationSubmitted,
    currentRecordingId,
    reviewerMaterials,
    loadReviewerMaterials,
    viewMaskOverlay,
    maskOverlayOpacity,
  };
}
