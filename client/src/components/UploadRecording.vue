<script lang="ts">
import { defineComponent, PropType, ref, Ref } from 'vue';
import { RecordingMimeTypes } from '../constants';
import useRequest from '../use/useRequest';
import { patchRecording, uploadRecordingFile } from '../api/api';
import { VDatePicker } from 'vuetify/labs/VDatePicker';

export interface EditingRecording {
  id: number,
  name: string,
  date: string,
  equipment: string,
  comments: string,
  public: boolean;
}
export default defineComponent({
  components: {
    VDatePicker,
  },
  props: {
    editing: {
      type: Object as PropType<EditingRecording | null>,
      default: () => null,
    }
  },
  emits: ['done', 'cancel'],
  setup(props, { emit }) {
    const fileInputEl: Ref<HTMLInputElement | null> = ref(null);
    const fileModel: Ref<File | undefined> = ref();
    const successfulUpload = ref(false);
    const errorText = ref('');
    const progressState = ref('');
    const recordedDate = ref(props.editing ? props.editing.date : new Date().toISOString().split('T')[0]); // YYYY-MM-DD Time
    const uploadProgress = ref(0);
    const name = ref(props.editing ? props.editing.name : '');
    const equipment = ref(props.editing ? props.editing.equipment : '');
    const comments = ref(props.editing ? props.editing.comments : '');
    const validForm = ref(false);
    const publicVal = ref(props.editing ? props.editing.public : false);
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


    const { request: submit, loading: submitLoading } = useRequest(async () => {
      const file = fileModel.value;
      if (!file) {
        throw new Error('Unreachable');
      }
      await uploadRecordingFile(file, name.value, recordedDate.value, equipment.value, comments.value, publicVal.value);
      emit('done');
    });

    const handleSubmit = async () => {
      if (props.editing) {
        await patchRecording(props.editing.id, name.value, recordedDate.value, equipment.value, comments.value, publicVal.value);
        emit('done');
      } else {
        submit();
      }
    };

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const updateTime = (time: any)  => {
    recordedDate.value = new Date(time as string).toISOString().split('T')[0];
  };

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
      recordedDate,
      validForm,
      publicVal,
      selectFile,
      readFile,
      handleSubmit,
      updateTime,
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
      width="100%"
      style="max-height:90vh; overflow-y: scroll"
    >
      <v-container>
        <v-card-title>
          {{ editing ? 'Edit' : 'Upload' }} Recording
        </v-card-title>
        <v-card-text>
          <v-form v-model="validForm">
            <v-row
              v-if="errorText === '' && progressState === '' && fileModel !== undefined && !editing"
              class="mx-2"
            >
              Upload {{ fileModel.name }} ?
            </v-row>
            <v-row
              v-else-if="fileModel === undefined && !editing"
              class="mx-2 my-2"
            >
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
            <v-row
              v-else-if="progressState !== '' && !editing"
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
              v-else-if="!editing"
              class="mx-2"
            >
              <v-alert type="error">
                {{ errorText }}
              </v-alert>
            </v-row>
            <v-row>
              <v-text-field
                v-model="name"
                label="name"
                :rules="[ v => !!v || 'Requires a name']"
              />
            </v-row>
            <v-row>
              <v-checkbox
                v-model="publicVal"
                label="Public"
                hint="Share Recording with other Users"
                persistent-hint
              />
            </v-row>
            <v-row class="pb-4">
              <v-menu
                open-delay="20"
                :close-on-content-click="false"
              >
                <template #activator="{ props:subProps }">
                  <v-btn
                    color="primary"
                    v-bind="subProps"
                    class="mr-2"
                  >
                    <b>Recorded:</b>
                    <span> {{ recordedDate }}</span>
                  </v-btn>
                </template>
                <v-date-picker
                  :model-value="[recordedDate]"
                  hide-actions
                  @update:model-value="updateTime($event)"
                />
              </v-menu>
            </v-row>
            <v-row>
              <v-expansion-panels>
                <v-expansion-panel>
                  <v-expansion-panel-title>Details</v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <v-row>
                      <v-text-field
                        v-model="equipment"
                        label="equipment"
                      />
                    </v-row>
                    <v-row>
                      <v-text-field
                        v-model="comments"
                        label="comments"
                      />
                    </v-row>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>
            </v-row>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            @click="$emit('cancel', true)"
          >
            Cancel
          </v-btn>
          <v-btn
            :disabled=" (!fileModel && !editing) || errorText !== '' || submitLoading || !validForm"
            color="primary"
            @click="handleSubmit"
          >
            <span v-if="!submitLoading">
              Submit
            </span>
            <v-icon v-else>
              mdi-loading mdi-spin
            </v-icon>
          </v-btn>
        </v-card-actions>
      </v-container>
    </v-card>
  </div>
</template>
