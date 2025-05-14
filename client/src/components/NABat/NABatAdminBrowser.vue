<script lang="ts">
import { defineComponent, ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import MapLocation from '@components/MapLocation.vue';
import {
  getNABatConfigurationRecordings,
  getNABatConfigurationAnnotations,
  type RecordingListItem,
  type Annotation,
} from '@api/NABatApi';

export default defineComponent({
  name: 'NABatAdminBrowser',
  components:{
    MapLocation,
  },
  setup() {
    const router = useRouter();
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
      { title: 'View', value: 'view', sortable: false },
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

    function formatDate(isoString: string | null): string {
      if (!isoString) return '';
      const date = new Date(isoString);
      return new Intl.DateTimeFormat('en-CA', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }).format(date).replace(',', '');
    }

    async function fetchRecordings({ page, itemsPerPage }: { page: number; itemsPerPage: number }) {
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

    async function updateAnnotations({ page, itemsPerPage }: { page: number; itemsPerPage: number }) {
      filters.value.offset = (page - 1) * itemsPerPage;
      filters.value.limit = itemsPerPage;
      loading.value = true;
      try {
        if (selectedRecordingId.value !== null) {
          const data = await getNABatConfigurationAnnotations(selectedRecordingId.value);
          annotations.value = data.items;
          totalAnnotations.value = data.count;
        }
      } catch (error) {
        console.error('Failed to update annotations:', error);
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

    onMounted(() => fetchRecordings({ page: 1, itemsPerPage: 5 }));

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
      totalAnnotations,
      formatDate,
      router,
    };
  },
});
</script>

<template>
  <v-container fluid>
    <div v-if="!selectedRecordingId">
      <v-card class="pa-4">
        <v-card-title>Recordings</v-card-title>
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

          <template #item.created="{ item }">
            {{ formatDate(item.created) }}
          </template>
          <template #item.recording_location="{ item }">
            <v-menu
              v-if="item.recording_location"
              open-on-hover
              :close-on-content-click="false"
            >
              <template #activator="{ props }">
                <v-icon v-bind="props">
                  mdi-map
                </v-icon>
              </template>
              <v-card>
                <map-location
                  :editor="false"
                  :size="{width: 400, height: 400}"
                  :location="{ x: item.recording_location.coordinates[0], y: item.recording_location.coordinates[1]}"
                />
              </v-card>
            </v-menu>
          </template>
          <template #item.view="{ item }">
            <a
              :href="`/nabat/${item.id}/spectrogram`"
              target="_blank"
              rel="noopener"
            >
              <v-btn
                variant="outlined"
                size="small"
                color="primary"
              >
                View
              </v-btn>
            </a>
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
