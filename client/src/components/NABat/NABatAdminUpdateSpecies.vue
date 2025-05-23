<script lang="ts">
import { defineComponent, ref } from 'vue';
import { getProcessingTaskDetails, adminNaBatUpdateSpecies } from '../../api/api';
export default defineComponent({
  name: 'NaBatAdminUpdateSpecies',
  setup() {
    const apiToken = ref('');
    const taskId = ref<string | null>(null);
    const loading = ref(false);
    const taskInfo = ref('');
    const errorMessage = ref('');
    let timeoutId: number | null = null;

    const updateSpeciesList = async () => {
      loading.value = true;
      errorMessage.value = '';
      taskInfo.value = '';
      try {
        const response = await adminNaBatUpdateSpecies(apiToken.value);
        taskId.value = response.data.taskId;
        fetchTaskDetails();
      } catch (error) {
        loading.value = false;
        errorMessage.value = 'Failed to start species list update.';
      }
    };

    const fetchTaskDetails = async () => {
      if (taskId.value) {
        try {
          const response = await getProcessingTaskDetails(taskId.value);
          if (response.celery_data.status === 'Complete') {
            loading.value = false;
            clearPolling();
            taskInfo.value = 'Species list update complete.';
            return;
          } else if (response.celery_data.status === 'Error') {
            loading.value = false;
            errorMessage.value = response.celery_data.error || 'An error occurred.';
            clearPolling();
            return;
          } else if (response.celery_data.info?.description) {
            taskInfo.value = response.celery_data.info.description;
          }
        } catch (error) {
          loading.value = false;
          errorMessage.value = 'Failed to fetch task details.';
          clearPolling();
        }
      }
      timeoutId = window.setTimeout(fetchTaskDetails, 1000);
    };

    const clearPolling = () => {
      if (timeoutId !== null) {
        clearTimeout(timeoutId);
        timeoutId = null;
      }
    };

    return {
      apiToken,
      loading,
      taskInfo,
      errorMessage,
      updateSpeciesList,
    };
  },
});
</script>

<template>
  <v-card-title class="text-h6">
    Update Species List
  </v-card-title>
  
  <v-card-text>
    <v-text-field
      v-model="apiToken"
      label="API Token"
      :disabled="loading"
      outlined
      dense
      hide-details
      placeholder="Enter your API token"
    />
  
    <v-btn
      :loading="loading"
      :disabled="loading || !apiToken"
      color="primary"
      block
      class="mt-4"
      @click="updateSpeciesList"
    >
      Update Species List
    </v-btn>
  
    <div
      v-if="taskInfo"
      class="mt-2 text-body-2 text-grey"
    >
      {{ taskInfo }}
    </div>
  
    <div
      v-if="errorMessage"
      class="mt-2 text-body-2 text-error"
    >
      {{ errorMessage }}
    </div>
  </v-card-text>
</template>
  
<style scoped>
/* You can customize more styles here */
</style>
