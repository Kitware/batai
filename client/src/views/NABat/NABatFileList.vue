<script lang="ts">
import { defineComponent, onMounted, ref, type Ref } from "vue";
import { postNABatFileListCreate, type NABatFileListCreateResponse } from "@api/NABatApi";

// Dummy placeholder view: just fires the create call and dumps the raw
// response, to exercise the file-list auth + create flow end to end before
// a real progress/listing UI exists.
export default defineComponent({
  props: {
    fileListId: {
      type: Number,
      required: true,
    },
  },
  setup(props) {
    const loading = ref(true);
    const errorMessage: Ref<string | null> = ref(null);
    const response: Ref<NABatFileListCreateResponse | null> = ref(null);

    onMounted(async () => {
      try {
        response.value = await postNABatFileListCreate(props.fileListId);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } catch (error: any) {
        errorMessage.value = error.response?.data?.error ?? `Failed to create file list: ${error}`;
      } finally {
        loading.value = false;
      }
    });

    return {
      loading,
      errorMessage,
      response,
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
          <pre v-else>{{ JSON.stringify(response, null, 2) }}</pre>
        </v-col>
        <v-spacer />
      </v-row>
    </v-card-text>
  </v-card>
</template>
