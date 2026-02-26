<script lang="ts">
import { defineComponent } from 'vue';
import useState from '@use/useState';
import useRecording from '@use/useRecording';
import RecordingInfoDisplay from './RecordingInfoDisplay.vue';


export default defineComponent({
  components: {
    RecordingInfoDisplay
  },
  emits: ['close'],
  setup() {
    const { recordingInfo } = useRecording();
    const { configuration } = useState();

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
    @close="$emit('close')"
  />
</template>
