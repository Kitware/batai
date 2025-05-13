<script lang="ts">
import { defineComponent, ref, onMounted, watch } from 'vue';
import {
  getNABatConfigurationRecordings,
  getNABatConfigurationAnnotations,
  type RecordingListItem,
  type Annotation,
} from '@api/NABatApi'; // Adjust import path as needed

export default defineComponent({
  name: 'NABatAdminBrowser',
  setup() {
    const recordings = ref<RecordingListItem[]>([]);
    const annotations = ref<Annotation[]>([]);
    const totalRecordings = ref<number>(0);
    const totalAnnotations = ref<number>(0);
    const selectedRecordingId = ref<number | null>(null);
    const loading = ref(false);

    const filters = ref<{
      recording_id?: number;
      survey_event_id?: number;
      offset?: number;
      limit?: number;
    }>({});

    const recordingHeaders = [
      { title: 'Recording ID', value: 'recording_id' },
      { title: 'Survey Event ID', value: 'survey_event_id' },
      { title: 'Name', value: 'name' },
      { title: 'Created', value: 'created' },
      { title: 'Location', value: 'recording_location' },
      { title: 'Annotations', value: 'annotation_count' },
    ];

    const annotationHeaders = [
      { title: 'ID', value: 'id' },
      { title: 'User Email', value: 'user_email' },
      { title: 'Species', value: 'species' },
      { title: 'Confidence', value: 'confidence' },
      { title: 'Comments', value: 'comments' },
      { title: 'Model', value: 'model' },
      { title: 'Created', value: 'created' },
    ];

    async function fetchRecordings({page, itemsPerPage}: {page: number, itemsPerPage: number}) {
      filters.value.offset = (page - 1) * itemsPerPage;
      filters.value.limit = itemsPerPage;
      loading.value = true;
      try {
        const data = await getNABatConfigurationRecordings(filters.value);
        recordings.value = data.items;
        totalRecordings.value = data.count;
      } catch (error) {
        console.error('Failed to load recordings:', error);
      } finally {
        loading.value = false;
      }
    }

    async function fetchAnnotations(recordingId: number) {
      loading.value = true;
      try {
        const data = await getNABatConfigurationAnnotations(recordingId);
        annotations.value = data.items;
        totalAnnotations.value = data.count;
      } catch (error) {
        console.error('Failed to load annotations:', error);
      } finally {
        loading.value = false;
      }
    }

    async function updateAnnotations( {page, itemsPerPage}: {page: number, itemsPerPage: number}) {
      filters.value.offset = (page - 1) * itemsPerPage;
      filters.value.limit = itemsPerPage;
      loading.value = true;
      try {
        const data = await getNABatConfigurationAnnotations(selectedRecordingId.value);
        annotations.value = data.items;
        totalAnnotations.value = data.count;
      } catch (error) {
        console.error('Failed to load annotations:', error);
      } finally {
        loading.value = false;
      }
    }

    function selectRecording(item: RecordingListItem) {
      selectedRecordingId.value = item.id;
      if (selectedRecordingId.value !== null) {
        fetchAnnotations(selectedRecordingId.value);
      }
    }

    function goBack() {
      selectedRecordingId.value = null;
      annotations.value = [];
    }

    onMounted(() => fetchRecordings({page: 1, itemsPerPage: 5}));

    return {
      filters,
      loading,
      recordings,
      annotations,
      recordingHeaders,
      annotationHeaders,
      selectedRecordingId,
      totalRecordings,
      selectRecording,
      goBack,
      updateAnnotations,
      fetchRecordings,
      totalAnnotations
    };
  },
});
</script>

<template>
  <v-container fluid>
    <div v-if="!selectedRecordingId">
      <v-card class="pa-4">
        <v-card-title>
          Recordings
        </v-card-title>
        <v-data-table-server
          :headers="recordingHeaders"
          :items="recordings"
          :loading="loading"
          :items-per-page="5"
          :items-length="totalRecordings"
          class="elevation-1"
          style="max-height: 50vh;"
          @update:options="fetchRecordings"
        >
          <template #item.recording_id="{ item }">
            <v-btn
              variant="text"
              @click.stop="selectRecording(item)"
            >
              {{ item.recording_id }}
            </v-btn>
          </template>
        </v-data-table-server>
      </v-card>
    </div>

    <div v-else>
      <v-card class="pa-4">
        <v-card-title>
          Annotations for Recording ID: {{ selectedRecordingId }}
          <v-spacer />
          <v-btn
            color="primary"
            @click="goBack"
          >
            Back
          </v-btn>
        </v-card-title>

        <v-data-table-server
          :headers="annotationHeaders"
          :items="annotations"
          :loading="loading"
          :items-per-page="5"
          :items-length="totalAnnotations"
          class="elevation-1"
          style="max-height: 50vh;"
          @update:options="updateAnnotations"
        />
      </v-card>
    </div>
  </v-container>
</template>

<style scoped>
.v-btn {
  min-width: unset;
}
</style>
