<script lang="ts">
import { defineComponent, ref, Ref } from 'vue';
import { RecordingMimeTypes } from '../constants';
import { uploadRecordingFile } from '../api/api';

export default defineComponent({
  setup(props, { emit }) {
    const fileInputEl: Ref<HTMLInputElement | null> = ref(null);
    const fileModel: Ref<File | undefined> = ref();
    const successfulUpload = ref(false);
    const errorText = ref('');
    const progressState = ref('');
    const name = ref('');
    const equipment = ref('');
    const comments = ref('');
    const uploading = ref(false);
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
    const uploadFiles = (async () => {
      const file = fileModel.value;
      if (!file) {
        throw new Error('Unreachable');
      }
      uploading.value = true;
      await uploadRecordingFile(file, name.value, equipment.value, comments.value);
      uploading.value = false;
      successfulUpload.value = true;
      emit('done');
    });
    return {
      errorText,
      fileModel,
      fileInputEl,
      uploadFiles,
      successfulUpload,
      progressState,
      name,
      equipment,
      comments,
      selectFile,
      readFile,
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
          :disabled="uploading"
          @click="$emit('cancel', true)"
        >
          Cancel
        </v-btn>
        <v-btn
          :disabled="!fileModel ||errorText !== '' || submitLoading"
          color="primary"
          variant="contained-text"
          @click="uploadFiles"
        >
          <span v-if="!uploading">
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
