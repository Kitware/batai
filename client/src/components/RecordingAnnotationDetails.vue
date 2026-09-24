<script lang="ts">
import { defineComponent, ref, onMounted, type PropType } from "vue";
import {
  type FileAnnotationDetails,
  getFileAnnotationDetails,
} from "../api/api";
import { getNABatFileAnnotationDetails } from "../api/NABatApi";
import useState from '@/use/useState';

export default defineComponent({
  props: {
    recordingId: {
      type: Number as PropType<number>,
      required: true,
    },
  },
  emits: ["close"],
  setup(props, { emit }) {
    const annotationData = ref<FileAnnotationDetails | null>(null);
    const loading = ref(true);

    const { isNaBat } = useState();

    onMounted(async () => {
      try {
        const response = isNaBat()
          ? await getNABatFileAnnotationDetails(props.recordingId)
          : await getFileAnnotationDetails(props.recordingId);
        annotationData.value = response.data.details;
      } catch (error) {
        console.error("Error fetching annotation details:", error);
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
        <v-icon @click="$emit('close')"> mdi-close </v-icon>
      </v-row>
    </v-card-title>
    <v-card-text>
      <div>
        <h3>
          {{ annotationData.label }} (Score:
          {{ annotationData.score.toFixed(2) }})
        </h3>
        <v-data-table
          :headers="[
            { title: 'Label', value: 'label', sortable: true },
            { title: 'Confidence', value: 'value', sortable: true },
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
