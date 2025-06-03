<script lang="ts">
import { defineComponent, ref, onMounted, onBeforeUnmount } from 'vue';
import { getExportStatus } from '@api/api';
export default defineComponent({
  name: 'ExportStatusDialog',
  props: {
    exportId: {
      type: Number,
      required: true,
    },
  },
  emits: ['exit'],
  setup(props, { emit }) {
    const dialog = ref(true);
    const loading = ref(true);
    const error = ref<string | null>(null);
    let intervalId: number | undefined;

    const checkStatus = async () => {
      try {
        const status = await getExportStatus(props.exportId);
        console.log(status);
        if (status.status === 'complete' && status.downloadUrl) {
          clearPolling();
          window.location.href = status.downloadUrl;
          emit('exit');
        } else if (status.status === 'failed') {
          clearPolling();
          error.value = 'Export failed. Please try again.';
        }
      } catch (e) {
        clearPolling();
        error.value = 'An error occurred while checking export status.';
      }
    };

    const startPolling = () => {
      intervalId = window.setInterval(checkStatus, 1000);
    };

    const clearPolling = () => {
      if (intervalId !== undefined) {
        clearInterval(intervalId);
        intervalId = undefined;
      }
      loading.value = false;
    };

    const cancel = () => {
      clearPolling();
      dialog.value = false;
      emit('exit');
    };

    onMounted(() => {
      startPolling();
    });

    onBeforeUnmount(() => {
      clearPolling();
    });

    return {
      dialog,
      loading,
      error,
      cancel,
    };
  },
});
</script>

<template>
  <v-dialog
    v-model="dialog"
    max-width="500"
  >
    <v-card>
      <v-card-title>Export in Progress</v-card-title>
      <v-card-text>
        <v-progress-circular
          v-if="loading"
          indeterminate
          color="primary"
          class="mr-4"
        />
        <span v-if="loading">Waiting for export to complete...</span>
        <span
          v-if="error"
          class="text-error"
        >{{ error }}</span>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn
          @click="cancel"
        >
          Cancel
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>


<style scoped>
</style>