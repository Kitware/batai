<script lang="ts">
import {
  computed,
  defineComponent,
  ref,
  Ref,
  onMounted,
  watch,
} from 'vue';
import {
  deleteRecording,
  getRecordings,
  Recording,
  FileAnnotation,
  getRecordingTags,
  type RecordingListParams,
} from '../api/api';
import UploadRecording, { EditingRecording } from '@components/UploadRecording.vue';
import MapLocation from '@components/MapLocation.vue';
import useState from '@use/useState';
import BatchUploadRecording from '@components/BatchUploadRecording.vue';
import RecordingInfoDisplay from '@components/RecordingInfoDisplay.vue';
import RecordingAnnotationSummary from '@components/RecordingAnnotationSummary.vue';

/* Sort fields supported by the recordings list API (RecordingListQuerySchema.sort_by) */
const SERVER_SORT_FIELDS: readonly string[] = ['id', 'name', 'created', 'modified', 'recorded_date', 'owner_username'];

export default defineComponent({
  components: {
    UploadRecording,
    MapLocation,
    BatchUploadRecording,
    RecordingInfoDisplay,
    RecordingAnnotationSummary,
  },
  setup() {
    const {
      sharedList,
      recordingList,
      recordingTagList,
      currentUser,
      configuration,
      showSubmittedRecordings,
      myRecordingsDisplay,
      sharedRecordingsDisplay,
    } = useState();
    const editingRecording: Ref<EditingRecording | null> = ref(null);
    let intervalRef: number | null = null;

    const totalMyCount = ref(0);
    const totalSharedCount = ref(0);
    const lastMyOptions = ref<{ page: number; itemsPerPage: number; sortBy?: { key: string; order: string }[] }>({ page: 1, itemsPerPage: 20 });
    const lastSharedOptions = ref<{ page: number; itemsPerPage: number; sortBy?: { key: string; order: string }[] }>({ page: 1, itemsPerPage: 20 });

    const uploadDialog = ref(false);
    const batchUploadDialog = ref(false);
    const sortByMy = ref<{ key: string; order: 'asc' | 'desc' }[]>([{ key: 'created', order: 'desc' }]);
    const sortByShared = ref<{ key: string; order: 'asc' | 'desc' }[]>([{ key: 'created', order: 'desc' }]);

    const myRecordingsLoading = ref(false);
    const sharedRecordingsLoading = ref(false);

    const headers: Ref<{
      title: string;
      key: string;
      value: string;
      sortable?: boolean;
      valueFn?: (item: Recording) => boolean | string | number;
    }[]> = ref([
        { title: 'Name', key: 'name', value: 'name', sortable: SERVER_SORT_FIELDS.includes('name') },
        { title: 'Annotation', key: 'annotation', value: 'annotation', sortable: SERVER_SORT_FIELDS.includes('annotation') },
        { title: 'Owner', key: 'owner_username', value: 'owner_username', sortable: SERVER_SORT_FIELDS.includes('owner_username') },
        { title: 'Tags', key: 'tag_text', value: 'tag_text', sortable: SERVER_SORT_FIELDS.includes('tag_text') },
        { title: 'Recorded Date', key: 'recorded_date', value: 'recorded_date', sortable: SERVER_SORT_FIELDS.includes('recorded_date') },
        { title: 'Public', key: 'public', value: 'public', sortable: SERVER_SORT_FIELDS.includes('public') },
        { title: 'GRTS CellId', key: 'grts_cell_id', value: 'grts_cell_id', sortable: SERVER_SORT_FIELDS.includes('grts_cell_id') },
        { title: 'Location', key: 'recording_location', value: 'recording_location', sortable: SERVER_SORT_FIELDS.includes('recording_location') },
        { title: 'Details', key: 'comments', value: 'comments', sortable: SERVER_SORT_FIELDS.includes('comments') },
        { title: 'User Pulse Annotations', key: 'userAnnotations', value: 'userAnnotations', sortable: SERVER_SORT_FIELDS.includes('userAnnotations') },
        { title: 'Edit', key: 'edit', value: 'edit', sortable: false },
    ]);

    const sharedHeaders = ref([
        { title: 'Name', key: 'name', value: 'name', sortable: SERVER_SORT_FIELDS.includes('name') },
        { title: 'Annotation', key: 'annotation', value: 'annotation', sortable: SERVER_SORT_FIELDS.includes('annotation') },
        { title: 'Owner', key: 'owner_username', value: 'owner_username', sortable: SERVER_SORT_FIELDS.includes('owner_username') },
        { title: 'Tags', key: 'tag_text', value: 'tag_text', sortable: SERVER_SORT_FIELDS.includes('tag_text') },
        { title: 'Recorded Date', key: 'recorded_date', value: 'recorded_date', sortable: SERVER_SORT_FIELDS.includes('recorded_date') },
        { title: 'Public', key: 'public', value: 'public', sortable: SERVER_SORT_FIELDS.includes('public') },
        { title: 'GRTS CellId', key: 'grts_cell_id', value: 'grts_cell_id', sortable: SERVER_SORT_FIELDS.includes('grts_cell_id') },
        { title: 'Location', key: 'recording_location', value: 'recording_location' },
        { title: 'Details', key: 'comments', value: 'comments', sortable: SERVER_SORT_FIELDS.includes('comments') },
        { title: 'Annotated by Me', key: 'userMadeAnnotations', value: 'userMadeAnnotations', sortable: SERVER_SORT_FIELDS.includes('userMadeAnnotations') },
    ]);

    function buildMyParams(options: { page: number; itemsPerPage: number; sortBy?: { key: string; order: string }[] }): RecordingListParams {
      const sortByFirst = options.sortBy?.[0];
      const sortBy = (sortByFirst?.key && (SERVER_SORT_FIELDS as readonly string[]).includes(sortByFirst.key))
        ? sortByFirst.key
        : 'created';
      const sort_direction = sortByFirst?.order === 'asc' ? 'asc' : 'desc';
      return {
        page: options.page,
        limit: options.itemsPerPage,
        sort_by: sortBy as RecordingListParams['sort_by'],
        sort_direction,
        tags: filterTags.value.length ? filterTags.value : undefined,
        exclude_submitted: configuration.value.mark_annotations_completed_enabled && !showSubmittedRecordings.value ? true : undefined,
      };
    }

    function buildSharedParams(options: { page: number; itemsPerPage: number; sortBy?: { key: string; order: string }[] }): RecordingListParams {
      const sortByFirst = options.sortBy?.[0];
      const sortBy = (sortByFirst?.key && (SERVER_SORT_FIELDS as readonly string[]).includes(sortByFirst.key))
        ? sortByFirst.key
        : 'created';
      const sort_direction = sortByFirst?.order === 'asc' ? 'asc' : 'desc';
      return {
        public: true,
        page: options.page,
        limit: options.itemsPerPage,
        sort_by: sortBy as RecordingListParams['sort_by'],
        sort_direction,
        tags: sharedFilterTags.value.length ? sharedFilterTags.value : undefined,
        exclude_submitted: configuration.value.mark_annotations_completed_enabled && !showSubmittedRecordings.value ? true : undefined,
      };
    }

    const fetchMyRecordings = async (options: { page: number; itemsPerPage: number; sortBy?: { key: string; order: string }[] }) => {
      const opts = { ...options, sortBy: options.sortBy ?? sortByMy.value };
      lastMyOptions.value = opts;
      myRecordingsLoading.value = true;
      try {
        const res = await getRecordings(false, buildMyParams(opts));
        recordingList.value = res.data.items;
        totalMyCount.value = res.data.count;
        let missingSpectro = false;
        for (let i = 0; i < recordingList.value.length; i += 1) {
          if (!recordingList.value[i].hasSpectrogram) {
            missingSpectro = true;
            break;
          }
        }
        if (missingSpectro && intervalRef === null) {
          intervalRef = setInterval(() => fetchMyRecordings(lastMyOptions.value), 5000);
        } else if (!missingSpectro && intervalRef !== null) {
          clearInterval(intervalRef);
          intervalRef = null;
        }
      } finally {
        myRecordingsLoading.value = false;
      }
    };

    const fetchSharedRecordings = async (options: { page: number; itemsPerPage: number; sortBy?: { key: string; order: string }[] }) => {
      const opts = { ...options, sortBy: options.sortBy ?? sortByShared.value };
      lastSharedOptions.value = opts;
      sharedRecordingsLoading.value = true;
      try {
        const res = await getRecordings(true, buildSharedParams(opts));
        sharedList.value = res.data.items;
        totalSharedCount.value = res.data.count;
      } finally {
        sharedRecordingsLoading.value = false;
      }
    };

    watch(showSubmittedRecordings, () => {
      fetchMyRecordings(lastMyOptions.value);
      fetchSharedRecordings(lastSharedOptions.value);
    });

    const fetchRecordingTags = async () => {
      const tags = await getRecordingTags();
      recordingTagList.value = tags.data;
    };

    const filterTags: Ref<string[]> = ref([]);
    const sharedFilterTags: Ref<string[]> = ref([]);
    const recordingTagOptions = computed(() =>
      recordingTagList.value.map((t) => t.text).filter(Boolean)
    );

    function currentUserSubmissionStatus(recording: Recording) {
      const userAnnotations = recording.fileAnnotations.filter((annotation: FileAnnotation) => (
        annotation.owner === currentUser.value && annotation.model === 'User Defined'
      ));
      if (userAnnotations.find((annotation: FileAnnotation) => annotation.submitted)) {
        return 1;
      }
      return userAnnotations.length ? 0 : -1;
    }

    function currentUserSubmission(recording: Recording) {
      const userSubmittedAnnotation = recording.fileAnnotations.find((annotation: FileAnnotation) => (
        annotation.owner === currentUser.value && annotation.submitted
      ));
      return userSubmittedAnnotation?.species[0]?.species_code || '';
    }

    function addSubmittedColumns() {
      if (configuration.value.mark_annotations_completed_enabled) {
        const submittedHeader = { title: 'Submission Status', key: 'submitted', value: 'submitted' };
        const myLabelHeader = { title: 'My Submitted Label', key: 'submittedLabel', value: 'submittedLabel' };
        headers.value.push(submittedHeader, myLabelHeader);
        sharedHeaders.value.push(submittedHeader, myLabelHeader);
      }
    }

    function hideDetailedMetadataColumns() {
      if (!configuration.value.mark_annotations_completed_enabled) return;
      const filterDetailedMetadataFunction = (val: { key: string }) => (
        !['comments', 'details', 'annotation', 'userAnnotations'].includes(val.key)
      );
      headers.value = headers.value.filter(filterDetailedMetadataFunction);
      sharedHeaders.value = sharedHeaders.value.filter(filterDetailedMetadataFunction);
    }

    const myRecordingListStyles = computed(() => {
      const sectionHeight = configuration.value.mark_annotations_completed_enabled ? '35vh' : '40vh';
      return {
        'height': sectionHeight,
        'max-height': sectionHeight,
      };
    });

    const sharedRecordingListStyles = computed(() => {
      let sectionHeight: string;
      if (configuration.value.mark_annotations_completed_enabled) {
        sectionHeight = '35vh';
      } else {
        sectionHeight = '40vh';
      }
      if (!configuration.value.is_admin && !configuration.value.non_admin_upload_enabled) {
        sectionHeight = '75vh';
      }
      return {
        'height': sectionHeight,
        'max-height': sectionHeight,
      };
    });

    onMounted(async () => {
      await fetchRecordingTags();
      addSubmittedColumns();
      hideDetailedMetadataColumns();
      await fetchMyRecordings({ page: 1, itemsPerPage: 20 });
      await fetchSharedRecordings({ page: 1, itemsPerPage: 20 });
    });

    watch(filterTags, () => fetchMyRecordings(lastMyOptions.value), { deep: true });
    watch(sharedFilterTags, () => fetchSharedRecordings(lastSharedOptions.value), { deep: true });

    const uploadDone = () => {
        uploadDialog.value = false;
        batchUploadDialog.value = false;
        editingRecording.value = null;
        fetchMyRecordings(lastMyOptions.value);
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
        const [ lon, lat ] = item.recording_location.coordinates;
        editingRecording.value['location'] = {lat, lon};
      }
      if (item.tags_text) {
        editingRecording.value.tags = item.tags_text.filter((tag: string) => !!tag);
      }
      uploadDialog.value = true;
    };
    const deleteDialogOpen = ref(false);
    const recordingToDelete: Ref<Recording | null> = ref(null);
    const openDeleteRecordingDialog = (recording: Recording) => {
      deleteDialogOpen.value = true;
      recordingToDelete.value = recording;
    };
    const deleteOneRecording = async () => {
      if (deleteDialogOpen.value && recordingToDelete.value) {
        deleteDialogOpen.value = false;
        await deleteRecording(recordingToDelete.value.id);
        recordingToDelete.value = null;
        fetchMyRecordings(lastMyOptions.value);
      }
    };

    return {
        headers,
        sharedHeaders,
        recordingList,
        sharedList,
        totalMyCount,
        totalSharedCount,
        uploadDialog,
        batchUploadDialog,
        filterTags,
        sharedFilterTags,
        recordingTagOptions,
        uploadDone,
        editRecording,
        deleteOneRecording,
        deleteDialogOpen,
        openDeleteRecordingDialog,
        recordingToDelete,
        editingRecording,
        myRecordingsLoading,
        sharedRecordingsLoading,
        currentUserSubmission,
        currentUserSubmissionStatus,
        configuration,
        myRecordingListStyles,
        sharedRecordingListStyles,
        showSubmittedRecordings,
        myRecordingsDisplay,
        sharedRecordingsDisplay,
        fetchMyRecordings,
        fetchSharedRecordings,
        sortByMy,
        sortByShared,
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
            label="Show submitted recordings"
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
              <v-list-item @click="uploadDialog=true">
                <v-list-item-title>Upload Recording</v-list-item-title>
              </v-list-item>
              <v-list-item @click="batchUploadDialog=true">
                <v-list-item-title>
                  Batch Upload
                </v-list-item-title>
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
      <v-data-table-server
        v-if="configuration.is_admin || configuration.non_admin_upload_enabled"
        v-model:sort-by="sortByMy"
        :headers="headers"
        :items="recordingList"
        :items-length="totalMyCount"
        :loading="myRecordingsLoading"
        items-per-page="20"
        :items-per-page-options="[{ value: 10, title: '10' }, { value: 20, title: '20' }, { value: 50, title: '50' }, { value: 100, title: '100' }]"
        density="compact"
        class="elevation-1 my-recordings"
        :style="myRecordingListStyles"
        @update:options="fetchMyRecordings"
      >
        <template #top>
          <div max-height="100px">
            <v-combobox
              v-model="filterTags"
              :items="recordingTagOptions"
              label="Filter recordings by tags"
              multiple
              chips
              closable-chips
              clearable
            />
          </div>
        </template>
        <template #item.edit="{ item }">
          <v-icon @click="editRecording(item)">
            mdi-pencil
          </v-icon>
          <v-icon
            color="error"
            @click="openDeleteRecordingDialog(item)"
          >
            mdi-delete
          </v-icon>
        </template>

        <template #item.name="{ item }">
          <router-link
            v-if="item.hasSpectrogram"
            :to="`/recording/${item.id.toString()}/spectrogram`"
          >
            {{ item.name }}
          </router-link>
          <div v-else>
            {{ item.name }}
            <v-tooltip bottom>
              <template #activator="{ props: subProps }">
                <span v-bind="subProps">
                  <v-icon color="warning">mdi-alert</v-icon>
                  <v-icon>mdi-sync mdi-spin</v-icon>
                </span>
              </template>
              <span>Waiting for spectrogram to be computed</span>
            </v-tooltip>
          </div>
        </template>
        <template #item.annotation="{ item }">
          <RecordingAnnotationSummary :file-annotations="item.fileAnnotations" />
        </template>

        <template #item.tag_text="{ item }">
          <span v-if="item.tags_text">
            <v-chip
              v-for="tag in item.tags_text"
              :key="tag"
              size="small"
            >
              {{ tag }}
            </v-chip>
          </span>
        </template>

        <template #item.recorded_date="{ item }">
          {{ item.recorded_date }} {{ item.recorded_time }}
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
                :grts-cell-id="configuration.mark_annotations_completed_enabled ? item.grts_cell_id || undefined : undefined"
              />
            </v-card>
          </v-menu>
          <v-icon
            v-else
            color="error"
          >
            mdi-close
          </v-icon>
        </template>

        <template #item.comments="{ item }">
          <v-menu
            v-if="item.comments !== undefined"
            open-on-click
            :close-on-content-click="false"
          >
            <template #activator="{ props }">
              <v-icon v-bind="props">
                mdi-information-outline
              </v-icon>
            </template>
            <recording-info-display
              :recording-info="item"
              :minimal-metadata="configuration.mark_annotations_completed_enabled"
              disable-button
            />
          </v-menu>
        </template>

        <template #item.public="{ item }">
          <v-icon
            v-if="item.public"
            color="success"
          >
            mdi-check
          </v-icon>
          <v-icon
            v-else
            color="error"
          >
            mdi-close
          </v-icon>
        </template>

        <template
          v-if="configuration.mark_annotations_completed_enabled"
          #item.submitted="{ item }"
        >
          <v-tooltip v-if="currentUserSubmissionStatus(item) === 1">
            <template #activator="{ props }">
              <v-icon
                v-bind="props"
                color="success"
              >
                mdi-check
              </v-icon>
            </template>
            You have submitted an annotation for this recording
          </v-tooltip>
          <v-tooltip v-else-if="currentUserSubmissionStatus(item) === 0">
            <template #activator="{ props }">
              <v-icon
                v-bind="props"
                color="warning"
              >
                mdi-circle-outline
              </v-icon>
            </template>
            You have created an annotation, but it has not been submitted
          </v-tooltip>
          <v-tooltip v-else>
            <template #activator="{ props }">
              <v-icon
                v-bind="props"
                color="error"
              >
                mdi-close
              </v-icon>
            </template>
            You have not created an annotation for this recording
          </v-tooltip>
        </template>
      </v-data-table-server>
      <div
        v-if="
          totalMyCount > 0
            && configuration.mark_annotations_completed_enabled
            && (configuration.is_admin || configuration.non_admin_upload_enabled)
        "
        class="d-flex justify-center align-center"
      >
        <span class="text-body-2">
          Total: {{ totalMyCount }} recording{{ totalMyCount !== 1 ? 's' : '' }}
        </span>
      </div>
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
        <div>
          Shared
        </div>
      </v-row>
    </v-card-title>
    <v-card-text>
      <v-data-table-server
        v-model:sort-by="sortByShared"
        :headers="sharedHeaders"
        :items="sharedList"
        :items-length="totalSharedCount"
        :loading="sharedRecordingsLoading"
        items-per-page="20"
        :items-per-page-options="[{ value: 10, title: '10' }, { value: 20, title: '20' }, { value: 50, title: '50' }, { value: 100, title: '100' }]"
        density="compact"
        class="elevation-1 shared-recordings"
        :style="sharedRecordingListStyles"
        @update:options="fetchSharedRecordings"
      >
        <template #top>
          <div max-height="100px">
            <v-combobox
              v-model="sharedFilterTags"
              :items="recordingTagOptions"
              label="Filter recordings by tags"
              multiple
              chips
              closable-chips
              clearable
            />
          </div>
        </template>
        <template #item.name="{ item }">
          <router-link
            :to="`/recording/${item.id.toString()}/spectrogram`"
          >
            {{ item.name }}
          </router-link>
        </template>
        <template #item.recorded_date="{ item }">
          {{ item.recorded_date }} {{ item.recorded_time }}
        </template>
        <template #item.annotation="{ item }">
          <RecordingAnnotationSummary :file-annotations="item.fileAnnotations" />
        </template>
        <template #item.public="{ item }">
          <v-icon
            v-if="item.public"
            color="success"
          >
            mdi-check
          </v-icon>
          <v-icon
            v-else
            color="error"
          >
            mdi-close
          </v-icon>
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
                :grts-cell-id="configuration.mark_annotations_completed_enabled ? item.grts_cell_id || undefined : undefined"
              />
            </v-card>
          </v-menu>
          <v-icon
            v-else
            color="error"
          >
            mdi-close
          </v-icon>
        </template>

        <template #item.comments="{ item }">
          <v-menu
            v-if="item.comments !== undefined"
            open-on-click
            :close-on-content-click="false"
          >
            <template #activator="{ props }">
              <v-icon v-bind="props">
                mdi-information-outline
              </v-icon>
            </template>
            <recording-info-display
              :recording-info="item"
              disable-button
            />
          </v-menu>
        </template>

        <template #item.userMadeAnnotations="{ item }">
          <v-icon
            v-if="item.userMadeAnnotations"
            color="success"
          >
            mdi-check
          </v-icon>
          <v-icon
            v-else
            color="error"
          >
            mdi-close
          </v-icon>
        </template>

        <template
          v-if="configuration.mark_annotations_completed_enabled"
          #item.submitted="{ item }"
        >
          <v-tooltip v-if="currentUserSubmissionStatus(item) === 1">
            <template #activator="{ props }">
              <v-icon
                v-bind="props"
                color="success"
              >
                mdi-check
              </v-icon>
            </template>
            You have submitted an annotation for this recording
          </v-tooltip>
          <v-tooltip v-else-if="currentUserSubmissionStatus(item) === 0">
            <template #activator="{ props }">
              <v-icon
                v-bind="props"
                color="warning"
              >
                mdi-circle-outline
              </v-icon>
            </template>
            You have created an annotation, but it has not been submitted
          </v-tooltip>
          <v-tooltip v-else>
            <template #activator="{ props }">
              <v-icon
                v-bind="props"
                color="error"
              >
                mdi-close
              </v-icon>
            </template>
            You have not created an annotation for this recording
          </v-tooltip>
        </template>
      </v-data-table-server>
      <div
        v-if="totalSharedCount > 0 && configuration.mark_annotations_completed_enabled"
        class="d-flex justify-center align-center"
      >
        <span class="text-body-2">
          Total: {{ totalSharedCount }} recording{{ totalSharedCount !== 1 ? 's' : '' }}
        </span>
      </div>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.my-recordings {
  overflow-y:scroll;
}
.shared-recordings {
  overflow-y:scroll;
}
</style>
