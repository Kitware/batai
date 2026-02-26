import { ref, Ref, watch } from "vue";
import { getPulseMetadata, PulseMetadata } from "../api/api";

const STORAGE_KEY = "pulseMetadata";

/** Single mode for pulse metadata labels: None, Always, Hover (inline labels), or Tooltip. */
export type PulseMetadataLabelsMode = "None" | "Always" | "Hover" | "Tooltip";

export const PULSE_METADATA_LABELS_OPTIONS: { title: string; value: PulseMetadataLabelsMode }[] = [
  { title: "None", value: "None" },
  { title: "Always", value: "Always" },
  { title: "Hover (labels)", value: "Hover" },
  { title: "Tooltip", value: "Tooltip" },
];

interface PulseMetadataStorage {
  viewPulseMetadataLayer?: boolean;
  pulseMetadataLineColor?: string;
  pulseMetadataLineSize?: number;
  pulseMetadataHeelColor?: string;
  pulseMetadataCharFreqColor?: string;
  pulseMetadataKneeColor?: string;
  pulseMetadataLabelColor?: string;
  pulseMetadataLabelFontSize?: number;
  pulseMetadataPointSize?: number;
  /** Replaces legacy pulseMetadataShowLabels, pulseMetadataShowLabelsOnHover, pulseMetadataHoverMode */
  pulseMetadataLabels?: PulseMetadataLabelsMode;
  pulseMetadataDurationFreqLineColor?: string;
}

function loadFromStorage(): Partial<PulseMetadataStorage> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      return JSON.parse(raw) as PulseMetadataStorage;
    }
  } catch {
    // ignore parse errors
  }
  return {};
}

function saveToStorage(data: PulseMetadataStorage) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // ignore quota errors
  }
}

const stored = loadFromStorage();

/** Migrate legacy storage keys to pulseMetadataLabels. */
function getInitialLabelsMode(): PulseMetadataLabelsMode {
  const storedLabels = stored.pulseMetadataLabels;
  if (storedLabels && ["None", "Always", "Hover", "Tooltip"].includes(storedLabels)) {
    return storedLabels as PulseMetadataLabelsMode;
  }
  return "Tooltip"; // default to Tooltip if no valid stored value
}

const pulseMetadataList: Ref<PulseMetadata[]> = ref([]);
const pulseMetadataLoading = ref(false);
const viewPulseMetadataLayer = ref(stored.viewPulseMetadataLayer ?? false);

async function loadPulseMetadata(recordingId: number) {
  pulseMetadataLoading.value = true;
  try {
    pulseMetadataList.value = await getPulseMetadata(recordingId);
  } finally {
    pulseMetadataLoading.value = false;
  }
}

function clearPulseMetadata() {
  pulseMetadataList.value = [];
}

const toggleViewPulseMetadataLayer = () => {
  viewPulseMetadataLayer.value = !viewPulseMetadataLayer.value;
};

// Pulse metadata display style (curve line + heel, char_freq, knee colors and sizes)
const pulseMetadataLineColor = ref(stored.pulseMetadataLineColor ?? "#00FFFF");
const pulseMetadataLineSize = ref(stored.pulseMetadataLineSize ?? 2);
const pulseMetadataHeelColor = ref(stored.pulseMetadataHeelColor ?? "#FF0088");
const pulseMetadataCharFreqColor = ref(stored.pulseMetadataCharFreqColor ?? "#00FF00");
const pulseMetadataKneeColor = ref(stored.pulseMetadataKneeColor ?? "#FF8800");
const pulseMetadataLabelColor = ref(stored.pulseMetadataLabelColor ?? "#FFFFFF");
const pulseMetadataLabelFontSize = ref(stored.pulseMetadataLabelFontSize ?? 12);
const pulseMetadataPointSize = ref(stored.pulseMetadataPointSize ?? 5);
const pulseMetadataLabels = ref<PulseMetadataLabelsMode>(getInitialLabelsMode());
const pulseMetadataDurationFreqLineColor = ref(
  stored.pulseMetadataDurationFreqLineColor ?? "#FFFF00",
);

watch(
  [
    viewPulseMetadataLayer,
    pulseMetadataLineColor,
    pulseMetadataLineSize,
    pulseMetadataHeelColor,
    pulseMetadataCharFreqColor,
    pulseMetadataKneeColor,
    pulseMetadataLabelColor,
    pulseMetadataLabelFontSize,
    pulseMetadataPointSize,
    pulseMetadataLabels,
    pulseMetadataDurationFreqLineColor,
  ],
  () => {
    saveToStorage({
      viewPulseMetadataLayer: viewPulseMetadataLayer.value,
      pulseMetadataLineColor: pulseMetadataLineColor.value,
      pulseMetadataLineSize: pulseMetadataLineSize.value,
      pulseMetadataHeelColor: pulseMetadataHeelColor.value,
      pulseMetadataCharFreqColor: pulseMetadataCharFreqColor.value,
      pulseMetadataKneeColor: pulseMetadataKneeColor.value,
      pulseMetadataLabelColor: pulseMetadataLabelColor.value,
      pulseMetadataLabelFontSize: pulseMetadataLabelFontSize.value,
      pulseMetadataPointSize: pulseMetadataPointSize.value,
      pulseMetadataLabels: pulseMetadataLabels.value,
      pulseMetadataDurationFreqLineColor: pulseMetadataDurationFreqLineColor.value,
    });
  },
);

export default function usePulseMetadata() {
  return {
    pulseMetadataList,
    pulseMetadataLoading,
    loadPulseMetadata,
    clearPulseMetadata,
    viewPulseMetadataLayer,
    toggleViewPulseMetadataLayer,
    pulseMetadataLineColor,
    pulseMetadataLineSize,
    pulseMetadataHeelColor,
    pulseMetadataCharFreqColor,
    pulseMetadataKneeColor,
    pulseMetadataLabelColor,
    pulseMetadataLabelFontSize,
    pulseMetadataPointSize,
    pulseMetadataLabels,
    pulseMetadataDurationFreqLineColor,
  };
}
