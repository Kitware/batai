
  <script lang="ts">
  import { defineComponent, ref, onMounted, onUnmounted, Ref} from 'vue';
import { getProcessingTaskDetails } from '../api/api';
import { postAcousticBatch } from '../api/NABatApi';
  
  export default defineComponent({
    props: {
      batchId: {
        type: Number,
        required: true,
      },
      apiToken: {
        type: String,
        required: true,
      },
    },
    setup(props) {
      const errorMessage: Ref<string | null> = ref(null);
      const loading = ref(true);
      const taskId: Ref<string | null> = ref(null);
      let timeoutId: ReturnType<typeof setTimeout> | null = null;
  
      const fetchTaskDetails = async () => {
        if (taskId.value) {
          try {
            const response = await getProcessingTaskDetails(taskId.value);
              if (response.celery_data.status === 'Complete') {
              loading.value = false;
              if (timeoutId !== null) {
                clearTimeout(timeoutId);
                timeoutId = null;
              }
              return;
            } else if (response.celery_data.status === 'Error') {
              loading.value = false;
              errorMessage.value = response.celery_data.error;
              return;
            }
          } catch (error) {
            loading.value = false;
            errorMessage.value = 'Failed to fetch task details';
          }
        }
        timeoutId = setTimeout(fetchTaskDetails, 5000);
      };
  
      onMounted(async () => {
        try {
          const response = await postAcousticBatch(props.batchId, props.apiToken);
          if ('error' in response && response.error) {
            loading.value = false;
            errorMessage.value = response.error;
          } if ('taskId' in response && response?.taskId && !response?.error) {
            taskId.value = response.taskId;
            timeoutId = setTimeout(fetchTaskDetails, 2000);
          } else {
            loading.value = false;
            // Load in new NABatSpectrogramViewer either by route or component
            console.log('Data is loaded, please start loading spectrogram');
          }
        } catch (error) {
          errorMessage.value = 'Failed to start processing';
          loading.value = false;
        }
      });
  
      onUnmounted(() => {
        if (timeoutId !== null) {
          clearTimeout(timeoutId);
          timeoutId = null;
        }
      });
  
      return {
        errorMessage,
        loading,
      };
    },
  });
  </script>
<template>
  <VCard>
    <VCardText>
      <VProgressCircular
        v-if="loading"
        indeterminate
      />
      <VAlert
        v-else-if="errorMessage"
        type="error"
      >
        {{ errorMessage }}
      </VAlert>
      <div v-else>
        <p>Load Spectrogram</p>
      </div>
    </VCardText>
  </VCard>
</template>
