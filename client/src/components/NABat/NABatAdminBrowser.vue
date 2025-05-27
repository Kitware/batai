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
    const sortBy = ref([{ key: 'created', order: 'desc' }]);
    const sortByAnnotations = ref([{ key: 'created', order: 'desc' }]);

    const filters = ref<{
      recording_id?: number;
      survey_event_id?: number;
      offset?: number;
      limit?: number;
      sort_by?: 'created' | 'recording_id' | 'survey_event_id' | 'annotation_count';
      sort_direction?: 'asc' | 'desc';
    }>({});

    const annotationFilters = ref<{
      offset?: number;
      limit?: number;
      sort_by?: 'created' | 'user_email' | 'confidence';
    sort_direction?: 'asc' | 'desc';
    }>({});

    const recordingHeaders = [
      { title: 'Name', value: 'name' },
      { title: 'Recording ID', value: 'recording_id', sortable: true },
      { title: 'View', value: 'view', sortable: false },
      {
        title: 'Annotations',
        value: 'annotation_count',
        sortable: true,
        sortRaw: (a: string, b: string) => (parseInt(a) - parseInt(b)),
      },
      { title: 'Created', value: 'created', sortable: true },
      { title: 'Survey Event ID', value: 'survey_event_id' },
      { title: 'Location', value: 'recording_location' },
    ];

    const annotationHeaders = [
      { title: 'ID', value: 'id' },
      { title: 'User Email', value: 'user_email', sortable: true },
      { title: 'Created', value: 'created', sortable: true },
      { title: 'Confidence', value: 'confidence', sortable: true },
      { title: 'Species', value: 'species' },
      { title: 'Comments', value: 'comments' },
      { title: 'Model', value: 'model' },
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
      if (sortBy.value?.length && ['created', 'recording_id', 'survey_event_id', 'annotation_count'].includes(sortBy.value[0].key)) {
        filters.value.sort_by = sortBy.value[0].key as 'created' | 'recording_id' | 'survey_event_id' | 'annotation_count';
        filters.value.sort_direction = sortBy.value[0].order === 'asc' ? 'asc' : 'desc';
      }
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
      annotationFilters.value.offset = (page - 1) * itemsPerPage;
      annotationFilters.value.limit = itemsPerPage;
      loading.value = true;
      try {
        if (selectedRecordingId.value !== null) {
          if (sortByAnnotations.value?.length && ['created', 'user_email', 'confidence'].includes(sortByAnnotations.value[0].key)) {
            annotationFilters.value.sort_by = sortByAnnotations.value[0].key as 'created' | 'user_email' | 'confidence';
            annotationFilters.value.sort_direction = sortByAnnotations.value[0].order === 'asc' ? 'asc' : 'desc';
          }
          const data = await getNABatConfigurationAnnotations(selectedRecordingId.value, annotationFilters.value);
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

    onMounted(() => fetchRecordings({ page: 1, itemsPerPage: 50 }));

    const sortByUpdate = (newSort?: { key: string; order: string }[]) => {
      if (newSort) {
        sortBy.value = newSort;
      } else {
        sortBy.value = [{ key: 'created', order: 'desc' }];
      }
    };

    const sortByUpdateAnnotations = (newSort?: { key: string; order: string }[]) => {
      if (newSort) {
        sortByAnnotations.value = newSort;
      } else {
        sortByAnnotations.value = [{ key: 'created', order: 'desc' }];
      }
    };

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
      sortBy,
      sortByUpdate,
      sortByAnnotations,
      sortByUpdateAnnotations,
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
          v-model:sort-by="sortBy"
          :headers="recordingHeaders"
          :items="recordings"
          :loading="loading"
          items-per-page="50"
          :items-per-page-options="[{value: 10, title: '10'}, {value: 25, title: '25'}, {value: 50, title: '50'}, {value: 100, title: '100'}]"
          :items-length="totalRecordings"
          class="elevation-1"
          style="max-height: 50vh;"
          @update:options="fetchRecordings"
          @update:sort-by="sortByUpdate"
        >
          <template #item.recording_id="{ item }">
            <v-btn
              color="primary"
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
          v-model:sort-by="sortByAnnotations"
          :headers="annotationHeaders"
          :items="annotations"
          :loading="loading"
          items-per-page="50"
          :items-length="totalAnnotations"
          :items-per-page-options="[{value: 10, title: '10'}, {value: 25, title: '25'}, {value: 50, title: '50'}, {value: 100, title: '100'}]"
          class="elevation-1"
          style="max-height: 50vh;"
          @update:options="updateAnnotations"
          @update:sort-by="sortByUpdateAnnotations"
        >
          <template #item.created="{ item }">
            {{ formatDate(item.created) }}
          </template>
        </v-data-table-server>
      </v-card>
    </div>
  </v-container>
</template>

<style scoped>
.v-btn {
  min-width: unset;
}
</style>
