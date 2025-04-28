
  <script lang="ts">
  import { defineComponent, ref, onMounted, onUnmounted, Ref, watch} from 'vue';
import { getProcessingTaskDetails } from '../api/api';
import { NABatRecordingDataResponse, postNABatRecording } from '../api/NABatApi';
import { useRouter } from 'vue-router';
import { usePrompt } from '../use/prompt-service';
import { useJWTToken } from '../use/useJWTToken';
  
  export default defineComponent({
    props: {
      recordingId: {
        type: Number,
        required: true,
      },
      surveyEventId: {
        type: Number,
        required: true,
      },
      apiToken: {
        type: String,
        required: true,
      },
    },
    setup(props) {

      const { prompt } = usePrompt();
      const { exp, shouldWarn, clear } = useJWTToken({
        'token': props.apiToken,
        'warningSeconds': 60,
      });
      const errorMessage: Ref<string | null> = ref(null);
      const additionalErrors: Ref<string[]> = ref([]);
        const loading = ref(true);
      const taskId: Ref<string | null> = ref(null);
      let timeoutId: ReturnType<typeof setTimeout> | null = null;
      const taskInfo = ref('');
      const router = useRouter();
  
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
              taskInfo.value = '';
              await checkNABatRecording();
              return;
            } else if (response.celery_data.status === 'Error') {
              loading.value = false;
              errorMessage.value = response.celery_data.error;
              taskInfo.value = '';
              return;
            } else if (response.celery_data.info?.description) {
              taskInfo.value = response.celery_data.info?.description;
            }
          } catch (error) {
            loading.value = false;
            errorMessage.value = 'Failed to fetch task details';
          }
        }
        timeoutId = setTimeout(fetchTaskDetails, 1000);
      };

      const checkNABatRecording = async () => {
        errorMessage.value = null;
        additionalErrors.value = [];
        try {
          const response = await postNABatRecording(props.recordingId, props.surveyEventId, props.apiToken);
          if ('error' in response && response.error) {
            loading.value = false;
            errorMessage.value = response.error;
          } if ('taskId' in response && response?.taskId && !response?.error) {
            taskId.value = response.taskId;
            timeoutId = setTimeout(fetchTaskDetails, 1000);
          } else {
            loading.value = false;
            // Load in new NABatSpectrogramViewer either by route or component
            const id = (response as NABatRecordingDataResponse).recordingId;
            router.push(`/nabat/${id}/spectrogram?apiToken=${props.apiToken}`);
          }
        } catch (error: AxiosError) {
          errorMessage.value = `Failed to start processing: ${error.message}:`;
          if (error.response.data.errors?.length) {
            additionalErrors.value = error.response.data.errors.map((item) => JSON.stringify(item));
          } else if (error.response.data.error) {
            additionalErrors.value.push(error.response.data.error);
          } else {
            additionalErrors.value.push('An unknown error occurred');
          }
          loading.value = false;
        }
      };
  
      onMounted(async () => {
        checkNABatRecording();
      });
  
      onUnmounted(async () => {
        if (timeoutId !== null) {
          clearTimeout(timeoutId);
          timeoutId = null;
        }
      });

      watch(shouldWarn, async() => {
        if (shouldWarn.value) {
          await prompt({
            title: 'API Token Expiration',
            text: [
              'The Api Token will expire in less than 60 seconds',
              'The Refresh option will be added in the future',
            ]
          });
        }
      }, { immediate: true });
  
      return {
        errorMessage,
        loading,
        taskInfo,
        additionalErrors,
      };
    },
  });
  </script>
<template>
  <v-card>
    <v-card-text>
      <v-row dense>
        <v-spacer />
        <v-col
          justify="center"
          cols="auto"
        >
          <v-progress-circular
            v-if="loading"
            indeterminate
            :size="256"
            :width="30"
            color="primary"
          >
            Loading...
          </v-progress-circular>
          <v-alert
            v-else-if="errorMessage"
            type="error"
          >
            {{ errorMessage }}
            <div v-if="additionalErrors.length">
              <ul>
                <li
                  v-for="(error, index) in additionalErrors"
                  :key="index"
                >
                  {{ error }}
                </li>
              </ul>
            </div>
          </v-alert>
          <h3
            v-if="loading && taskInfo"
            style="text-align: center"
          >
            {{ taskInfo }}
          </h3>
        </v-col>
        <v-spacer />
      </v-row>
    </v-card-text>
  </v-card>
</template>
