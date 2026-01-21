<script lang="ts">
import { defineComponent, onMounted, ref, Ref, watch } from 'vue';
import { getRecording, Recording } from '../api/api';
import useState from '@use/useState';
import RecordingInfoDisplay from './RecordingInfoDisplay.vue';


export default defineComponent({
  components: {
    RecordingInfoDisplay
  },
  props: {
    id: {
      type: String,
      required: true,
    },
  },
  emits: ['close'],
  setup(props) {
    const recordingInfo: Ref<Recording | null> = ref(null);
    const { configuration } = useState();

    const loadData = async () => {
      const recording = getRecording(props.id);
      recordingInfo.value = (await recording).data;
    };
    watch(() => props.id, () => loadData());
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
    @close="$emit('close')"
  />
</template>
