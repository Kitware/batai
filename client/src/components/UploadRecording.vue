<script lang="ts">
import { defineComponent, ref, Ref } from 'vue';
import { S3FileFieldProgress, S3FileFieldProgressState } from 'django-s3-file-field';
import { RecordingMimeTypes } from '../constants';
import useRequest from '../use/useRequest';
import { uploadRecordingFile } from '../api/api';

const progressStateMap: Record<S3FileFieldProgressState, string> = {
  [S3FileFieldProgressState.Initializing]: 'Initializing',
  [S3FileFieldProgressState.Sending]: 'Sending',
  [S3FileFieldProgressState.Finalizing]: 'Finalizing',
  [S3FileFieldProgressState.Done]: 'Done',
};
export default defineComponent({
  setup(props, { emit }) {
    const fileInputEl: Ref<HTMLInputElement | null> = ref(null);
    const fileModel: Ref<File | undefined> = ref();
    const successfulUpload = ref(false);
    const errorText = ref('');
    const progressState = ref('');
    const uploadProgress = ref(0);
    const name = ref('');
    const equipment = ref('');
    const comments = ref('');
    const readFile = (e: Event) => {
      const target = (e.target as HTMLInputElement);
      if (target?.files?.length) {
        const file = target.files.item(0);
        if (!file) {
          return;
        }
        if (!RecordingMimeTypes.includes(file.type)) {
          errorText.value = `Selected file is not one of the following types: ${RecordingMimeTypes.join(' ')}`;
          return;
        }
        fileModel.value = file;
      }
    };
    function selectFile() {
      if (fileInputEl.value !== null) {
        fileInputEl.value.click();
      }
    }
    function progressCallback (progress: S3FileFieldProgress) {
      if (progress.uploaded && progress.total) {
        uploadProgress.value = (progress.uploaded / progress.total) * 100;
      }
      progressState.value = progressStateMap[progress.state];
    }

    const { request: submit, loading: submitLoading } = useRequest(async () => {
      const file = fileModel.value;
      if (props.harvestId || !file) {
        throw new Error('Unreachable');
      }
      await uploadRecordingFile(file, name.value, equipment.value, comments.value, progressCallback);
      emit('done');
    });
    return {
      errorText,
      fileModel,
      fileInputEl,
      submitLoading,
      successfulUpload,
      progressState,
      uploadProgress,
      name,
      equipment,
      comments,
      selectFile,
      readFile,
      submit,
    };
  },
});
</script>

<template>
  <div
    style="height: 100%"
    class="d-flex pa-1"
  >
    <v-alert
      v-if="successfulUpload"
      v-model="successfulUpload"
      type="success"
      dismissible
    >
      Data successfully uploaded
    </v-alert>
    <input
      ref="fileInputEl"
      class="d-none"
      type="file"
      accept="audio/*"
      @change="readFile"
    >
    <v-card
      class="fill-height overflow-auto"
      width="100%"
    >
      <v-card-title class="text-h5">
        Upload Video
      </v-card-title>
      <v-col>
        <v-row
          v-if="errorText === '' && progressState === '' && fileModel !== undefined"
          class="mx-2"
        >
          Upload {{ fileModel.name }} ?
        </v-row>
        <v-row
          v-else-if="fileModel === undefined"
          class="mx-2"
        >
          <div>
            <v-row>
              <v-btn
                block
                color="primary"
                @click="selectFile"
              >
                <v-icon class="pr-2">
                  mdi-audio
                </v-icon>
                Choose Audio
              </v-btn>
            </v-row>
          </div>
        </v-row>
        <v-row
          v-else-if="progressState !== ''"
          class="mx-2"
        >
          <v-progress-linear
            v-model="uploadProgress"
            color="secondary"
            height="25"
            class="ma-auto text-xs-center"
          >
            <strong>{{ progressState }} : {{ Math.ceil(uploadProgress) }}%</strong>
          </v-progress-linear>
        </v-row>
        <v-row
          v-else
          class="mx-2"
        >
          <v-alert type="error">
            {{ errorText }}
          </v-alert>
        </v-row>
        <v-row>
          <div>
            <v-row>
              <v-text-field
                v-model="name"
                label="name"
              />
            </v-row>
            <v-row>
              <v-text-field
                v-model="equipment"
                label="equipment"
              />
            </v-row>
            <v-row>
              <v-text-area
                v-model="comments"
                label="comments"
              />
            </v-row>
          </div>
        </v-row>
      </v-col>
      <v-spacer class="grow" />
      <v-card-actions>
        <v-spacer />
        <v-btn
          variant="text"
          :disabled="submitLoading"
          @click="$emit('cancel', true)"
        >
          Cancel
        </v-btn>
        <v-btn
          :disabled="!fileModel ||errorText !== '' || submitLoading"
          color="primary"
          variant="contained-text"
          @click="submit"
        >
          <span v-if="!submitLoading">
            Submit
          </span>
          <v-icon v-else>
            mdi-loading mdi-spin
          </v-icon>
        </v-btn>
      </v-card-actions>
    </v-card>
  </div>
</template>
