<script lang="ts">
import { defineComponent, ref, onMounted, PropType } from 'vue';
import { FileAnnotationDetails, getFileAnnotationDetails } from '../api/api';
import { getNABatFileAnnotationDetails } from '../api/NABatApi';

export default defineComponent({
  props: {
    recordingId: {
      type: Number as PropType<number>,
      required: true,
    },
    apiToken: {
      type: String as PropType<string | undefined>,
      default: () => undefined,
    },
  },
  emits: ['close'],
  setup(props, { emit }) {
    const annotationData = ref<FileAnnotationDetails | null>(null);
    const loading = ref(true);

    onMounted(async () => {
      try {
        const response = props.apiToken ? await getNABatFileAnnotationDetails(props.recordingId, props.apiToken) : await getFileAnnotationDetails(props.recordingId);
        annotationData.value = response.data.details;
      } catch (error) {
        console.error('Error fetching annotation details:', error);
      } finally {
        loading.value = false;
      }
    });

    return { annotationData, loading, emit };
  },
});
</script>

<template>
  <v-card v-if="annotationData">
    <v-card-title>
      <v-row dense>
        Annotation Details
        <v-spacer />
        <v-icon @click="$emit('close')">
          mdi-close
        </v-icon>
      </v-row>
    </v-card-title>
    <v-card-text>
      <div>
        <h3>{{ annotationData.label }} (Score: {{ annotationData.score.toFixed(2) }})</h3>
        <v-data-table
          :headers="[
            { title: 'Label', value: 'label', sortable: true },
            { title: 'Value', value: 'value', sortable: true }
          ]"
          :items="annotationData.confidences"
          :items-per-page="-1"
          density="compact"
        >
          <template #bottom />
        </v-data-table>
      </div>
    </v-card-text>
  </v-card>
</template>
