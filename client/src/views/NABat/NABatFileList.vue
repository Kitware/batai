<script lang="ts">
import { defineComponent, onMounted, ref, type Ref } from "vue";
import { useRouter } from "vue-router";
import useNABatFileListQueue from "@/use/useNABatFileListQueue";

// Mirrors NABatRecording.vue's poll-then-redirect pattern: creates the list
// (or re-verifies access to an already-created one), waits for its first item
// to finish processing, then redirects into the spectrogram view - which owns
// the actual list-browsing UI (its File List sidebar tab) from here on.
export default defineComponent({
  props: {
    fileListId: {
      type: Number,
      required: true,
    },
  },
  setup(props) {
    const router = useRouter();
    const { createFileListAndWaitForFirst } = useNABatFileListQueue();
    const loading = ref(true);
    const errorMessage: Ref<string | null> = ref(null);
    const taskInfo = ref("");

    onMounted(async () => {
      try {
        const recordingId = await createFileListAndWaitForFirst(props.fileListId, (description) => {
          taskInfo.value = description;
        });
        router.push(`/nabat/${recordingId}/spectrogram?fileListId=${props.fileListId}`);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } catch (error: any) {
        errorMessage.value = error.message ?? `Failed to load file list: ${error}`;
        loading.value = false;
      }
    });

    return {
      loading,
      errorMessage,
      taskInfo,
    };
  },
});
</script>
<template>
  <v-card>
    <v-card-text>
      <v-row dense>
        <v-spacer />
        <v-col justify="center" cols="auto">
          <v-progress-circular v-if="loading" indeterminate :size="256" :width="30" color="primary">
            Loading...
          </v-progress-circular>
          <v-alert v-else-if="errorMessage" type="error">
            {{ errorMessage }}
          </v-alert>
          <h3 v-if="loading && taskInfo" style="text-align: center">
            {{ taskInfo }}
          </h3>
        </v-col>
        <v-spacer />
      </v-row>
    </v-card-text>
  </v-card>
</template>
