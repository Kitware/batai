<script lang="ts">
import { defineComponent, ref, Ref, onMounted } from 'vue';
import { deleteRecording, Recording, getRecordingTags } from '../api/api';
import UploadRecording, { EditingRecording } from '@components/UploadRecording.vue';
import useState from '@use/useState';
import BatchUploadRecording from '@components/BatchUploadRecording.vue';
import RecordingTable from '@components/RecordingTable.vue';

export default defineComponent({
  components: {
    UploadRecording,
    BatchUploadRecording,
    RecordingTable,
  },
  setup() {
    const { configuration, showSubmittedRecordings, recordingTagList } = useState();
    const editingRecording: Ref<EditingRecording | null> = ref(null);
    const uploadDialog = ref(false);
    const batchUploadDialog = ref(false);
    const deleteDialogOpen = ref(false);
    const recordingToDelete: Ref<Recording | null> = ref(null);
    const myRecordingsTableRef = ref<{ refetch?: () => void } | null>(null);

    async function fetchRecordingTags() {
      const tags = await getRecordingTags();
      recordingTagList.value = tags.data;
    }

    const uploadDone = () => {
      uploadDialog.value = false;
      batchUploadDialog.value = false;
      editingRecording.value = null;
      myRecordingsTableRef.value?.refetch?.();
    };

    const editRecording = (item: Recording) => {
      editingRecording.value = {
        name: item.name,
        equipment: item.equipment || '',
        comments: item.comments || '',
        date: item.recorded_date,
        time: item.recorded_time,
        public: item.public,
        id: item.id,
        siteName: item.site_name,
        software: item.software,
        detector: item.detector,
        speciesList: item.species_list,
        unusualOccurrences: item.unusual_occurrences,
      };
      if (item.recording_location) {
        const [lon, lat] = item.recording_location.coordinates;
        editingRecording.value['location'] = { lat, lon };
      }
      if (item.tags_text) {
        editingRecording.value.tags = item.tags_text.filter((tag: string) => !!tag);
      }
      uploadDialog.value = true;
    };

    const openDeleteRecordingDialog = (recording: Recording) => {
      deleteDialogOpen.value = true;
      recordingToDelete.value = recording;
    };

    const deleteOneRecording = async () => {
      if (deleteDialogOpen.value && recordingToDelete.value) {
        deleteDialogOpen.value = false;
        await deleteRecording(recordingToDelete.value.id);
        recordingToDelete.value = null;
        myRecordingsTableRef.value?.refetch?.();
      }
    };

    onMounted(() => {
      fetchRecordingTags();
    });

    return {
      configuration,
      showSubmittedRecordings,
      uploadDialog,
      batchUploadDialog,
      deleteDialogOpen,
      recordingToDelete,
      editingRecording,
      myRecordingsTableRef,
      uploadDone,
      editRecording,
      openDeleteRecordingDialog,
      deleteOneRecording,
    };
  },
});
</script>

<template>
  <v-card>
    <v-card-title>
      <v-row>
        <div v-if="configuration.is_admin || configuration.non_admin_upload_enabled">
          My Recordings
        </div>
        <v-spacer />
        <div class="d-flex justify-center align-center">
          <v-checkbox
            v-model="showSubmittedRecordings"
            class="mr-4"
            label="Show recordings with submitted annotations"
            hide-details
          />
          <v-menu v-if="configuration.is_admin || configuration.non_admin_upload_enabled">
            <template #activator="{ props }">
              <v-btn
                color="primary"
                v-bind="props"
              >
                Upload <v-icon>mdi-chevron-down</v-icon>
              </v-btn>
            </template>
            <v-list>
              <v-list-item @click="uploadDialog = true">
                <v-list-item-title>Upload Recording</v-list-item-title>
              </v-list-item>
              <v-list-item @click="batchUploadDialog = true">
                <v-list-item-title>Batch Upload</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </div>
      </v-row>
    </v-card-title>
    <v-card-text>
      <v-dialog
        v-model="deleteDialogOpen"
        width="auto"
      >
        <v-card>
          <v-card-title class="pa-4">
            Delete {{ recordingToDelete?.name || 'this recording' }}?
          </v-card-title>
          <v-card-actions class="pa-4">
            <v-btn
              variant="flat"
              @click="deleteDialogOpen = false"
            >
              Cancel
            </v-btn>
            <v-btn
              variant="flat"
              color="error"
              @click="deleteOneRecording()"
            >
              Delete
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
      <recording-table
        v-if="configuration.is_admin || configuration.non_admin_upload_enabled"
        ref="myRecordingsTableRef"
        variant="my"
        :edit-recording="editRecording"
        :open-delete-recording-dialog="openDeleteRecordingDialog"
      />
    </v-card-text>
    <v-dialog
      v-model="uploadDialog"
      width="700"
    >
      <upload-recording
        :editing="editingRecording"
        @done="uploadDone()"
        @cancel="uploadDialog = false; editingRecording = null"
      />
    </v-dialog>
    <v-dialog
      v-model="batchUploadDialog"
      width="700"
    >
      <batch-upload-recording
        @done="uploadDone()"
        @cancel="batchUploadDialog = false; editingRecording = null"
      />
    </v-dialog>
  </v-card>
  <v-card>
    <v-card-title>
      <v-row class="py-2">
        <div>Shared</div>
      </v-row>
    </v-card-title>
    <v-card-text>
      <recording-table variant="shared" />
    </v-card-text>
  </v-card>
</template>

<style scoped>
:deep(.my-recordings),
:deep(.shared-recordings) {
  overflow-y: scroll;
}
:deep(.my-recordings tr.current-recording-row),
:deep(.shared-recordings tr.current-recording-row) {
  border: 2px solid rgb(var(--v-theme-primary));
  box-sizing: border-box;
}
</style>
