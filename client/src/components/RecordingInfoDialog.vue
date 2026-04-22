<script lang="ts">
import {
  defineComponent,
  onMounted,
  ref,
  type Ref,
  watch,
  type PropType,
} from "vue";
import { getRecording, type Recording } from "../api/api";
import useState from "@use/useState";
import RecordingInfoDisplay from "./RecordingInfoDisplay.vue";

export default defineComponent({
  components: {
    RecordingInfoDisplay,
  },
  props: {
    id: {
      type: String,
      required: true,
    },
    displayMode: {
      type: String as PropType<"both" | "metadata" | "map">,
      default: "both",
    },
  },
  emits: ["close"],
  setup(props) {
    const recordingInfo: Ref<Recording | null> = ref(null);
    const { configuration } = useState();

    const loadData = async () => {
      const recording = getRecording(props.id);
      recordingInfo.value = (await recording).data;
    };
    watch(
      () => props.id,
      () => loadData(),
    );
    onMounted(() => loadData());
    return {
      recordingInfo,
      configuration,
    };
  },
});
</script>

<template>
  <recording-info-display
    v-if="recordingInfo"
    :recording-info="recordingInfo"
    :minimal-metadata="configuration.mark_annotations_completed_enabled"
    :display-mode="displayMode"
    @close="$emit('close')"
  />
</template>
