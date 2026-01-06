<script lang="ts">
import {
  computed,
  defineComponent,
  ref,
  Ref,
  onMounted,
} from 'vue';
import {
  deleteRecording,
  getRecordings,
  Recording,
  FileAnnotation,
  getRecordingTags,
} from '../api/api';
import UploadRecording, { EditingRecording } from '@components/UploadRecording.vue';
import MapLocation from '@components/MapLocation.vue';
import useState from '@use/useState';
import BatchUploadRecording from '@components/BatchUploadRecording.vue';
import RecordingInfoDisplay from '@components/RecordingInfoDisplay.vue';
import RecordingAnnotationSummary from '@components/RecordingAnnotationSummary.vue';
import { FilterFunction, InternalItem } from 'vuetify';

export default defineComponent({
  components: {
    UploadRecording,
    MapLocation,
    BatchUploadRecording,
    RecordingInfoDisplay,
    RecordingAnnotationSummary,
  },
  setup() {
    const itemsPerPage = ref(-1);
    const {
      sharedList,
      recordingList,
      recordingTagList,
      currentUser,
      configuration,
      loadCurrentUser,
      showSubmittedRecordings,
      submittedMyRecordings,
      submittedSharedRecordings,
      myRecordingsDisplay,
      sharedRecordingsDisplay,
    } = useState();
    const editingRecording: Ref<EditingRecording | null> = ref(null);
    let intervalRef: number | null = null;

    const uploadDialog = ref(false);
    const batchUploadDialog = ref(false);
    const headers: Ref<{
      title: string,
      key: string,
      value?: (item: Recording) => boolean | string | number,
    }[]> = ref([
        {
          title:'Name',
          key: 'name',
        },
        {
          title: 'Annotation',
          key: 'annotation',
        },
        {
          title:'Owner',
          key:'owner_username',
        },
        {
          title: 'Tags',
          key: 'tag_text',
        },
        {
          title:'Recorded Date',
          key:'recorded_date',
        },
        {
          title:'Public',
          key:'public',
        },
        {
          title:'GRTS CellId',
          key:'grts_cell_id',
        },
        {
          title: 'Location',
          key:'recording_location'
        },
        {
          title: 'Details',
          key:'comments'
        },
        {
          title:'Users Annotated',
          key:'userAnnotations',
        },
        {
          title:'Edit',
          key:'edit',
        },
    ]);

    const sharedHeaders = ref([
        {
          title: 'Name',
          key: 'name',
        },
        {
          title: 'Annotation',
          key: 'annotation'
        },
        {
          title: 'Owner',
          key: 'owner_username',
        },
        {
          title: 'Tags',
          key: 'tag_text',
        },
        {
          title: 'Recorded Date',
          key: 'recorded_date',
        },
        {
          title: 'Public',
          key: 'public',
        },
        {
          title: 'GRTS CellId',
          key: 'grts_cell_id',
        },
        {
          title: 'Location',
          key: 'details'
        },
        {
          title: 'Details',
          key: 'comments'
        },
        {
          title: 'Annotated by Me',
          key: 'userMadeAnnotations',
        },
    ]);
    const dataLoading = ref(false);
    const fetchRecordings = async () => {
      dataLoading.value = true;
      const recordings = await getRecordings();
      recordingList.value = recordings.data;
      // If we have a spectrogram being generated we need to refresh on an interval
      let missingSpectro = false;
      for (let i =0; i< recordingList.value.length; i+=1) {
        if (!recordingList.value[i].hasSpectrogram) {
          missingSpectro = true;
          break;
        }
      }
      if (missingSpectro) {
        if (intervalRef === null) {
          intervalRef = setInterval(() => fetchRecordings(), 5000);
        }
      } else  {
        if (intervalRef !== null) {
          clearInterval(intervalRef);
        }
      }
      const shared = await getRecordings(true);
      sharedList.value = shared.data;
      dataLoading.value = false;
    };

    const fetchRecordingTags = async () => {
      dataLoading.value = true;
      const tags = await getRecordingTags();
      recordingTagList.value = tags.data;
      dataLoading.value = false;
    };

    const filterTags: Ref<string[]> = ref([]);
    const sharedFilterTags: Ref<string[]> = ref([]);
    const recordingTags = computed(() => {
      const tags = new Set();
      recordingList.value.forEach((recording: Recording) => {
        recording.tags_text?.forEach((tag: string) => {
          if (tag) {
            tags.add(tag);
          }
        });
      });
      return Array.from(tags);
    });
    const sharedRecordingTags = computed(() => {
      const tags = new Set();
      sharedList.value.forEach((recording: Recording) => {
        recording.tags_text?.forEach((tag: string) => {
          if (tag) {
            tags.add(tag);
          }
        });
      });
      return Array.from(tags);
    });
    const tagFilter: FilterFunction = (value: string, search: string, item?: InternalItem<Recording>) => {
      if (filterTags.value.length === 0) {
        return true;
      }
      const filterTagSet = new Set(filterTags.value);
      const itemTagSet = new Set(item?.raw.tags_text);
      return filterTagSet.intersection(itemTagSet).size > 0;
    };
    const sharedTagFilter: FilterFunction = (value: string, search: string, item?: InternalItem<Recording>) => {
      if (filterTags.value.length === 0) {
        return true;
      }
      const filterTagSet = new Set(filterTags.value);
      const itemTagSet = new Set(item?.raw.tags_text);
      return filterTagSet.intersection(itemTagSet).size > 0;
    };

    function currentUserSubmission(recording: Recording) {
      const userSubmittedAnnotation = recording.fileAnnotations.find((annotation: FileAnnotation) => (
        annotation.owner === currentUser.value && annotation.submitted
      ));
      return userSubmittedAnnotation?.species[0]?.species_code;
    }

    function addSubmittedColumns() {
      if (configuration.value.mark_annotations_completed_enabled) {
        const submittedHeader = {
          title: 'Submitted',
          key: 'submitted',
          value: currentUserSubmission,
        };
        const myLabelHeader = {
          title: 'My Submitted Label',
          key: 'submittedLabel',
          value: currentUserSubmission,
        };
        headers.value.push(submittedHeader, myLabelHeader);
        sharedHeaders.value.push(submittedHeader, myLabelHeader);
      }
    }

    function hideDetailedMetadataColumns() {
      if (!configuration.value.mark_annotations_completed_enabled) return;
      const filterDetailedMetadataFunction = (val: { key: string }) => (
        !['recording_location', 'comments', 'details', 'annotation'].includes(val.key)
      );
      headers.value = headers.value.filter(filterDetailedMetadataFunction);
      sharedHeaders.value = sharedHeaders.value.filter(filterDetailedMetadataFunction);
    }

    const recordingListStyles = computed(() => {
      const sectionHeight = configuration.value.mark_annotations_completed_enabled ? '35vh' : '40vh';
      return {
        'height': sectionHeight,
        'max-height': sectionHeight,
      };
    });

    onMounted(async () => {
      await loadCurrentUser();
      await fetchRecordingTags();
      await fetchRecordings();
      addSubmittedColumns();
      hideDetailedMetadataColumns();
    });

    const uploadDone = () => {
        uploadDialog.value = false;
        batchUploadDialog.value = false;
        editingRecording.value = null;
        fetchRecordings();
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
        fetchRecordings();
      }
    };

    return {
        itemsPerPage,
        headers,
        sharedHeaders,
        recordingList,
        sharedList,
        uploadDialog,
        batchUploadDialog,
        tagFilter,
        sharedTagFilter,
        filterTags,
        sharedFilterTags,
        recordingTags,
        sharedRecordingTags,
        uploadDone,
        editRecording,
        deleteOneRecording,
        deleteDialogOpen,
        openDeleteRecordingDialog,
        recordingToDelete,
        editingRecording,
        dataLoading,
        currentUserSubmission,
        configuration,
        submittedMyRecordings,
        submittedSharedRecordings,
        recordingListStyles,
        showSubmittedRecordings,
        myRecordingsDisplay,
        sharedRecordingsDisplay,
     };
  },
});
</script>

<template>
  <v-card>
    <v-card-title>
      <v-row class="py-2">
        <div>
          My Recordings
        </div>
        <v-spacer />
        <div class="d-flex justify-center align-center">
          <v-checkbox
            v-if="configuration.mark_annotations_completed_enabled"
            v-model="showSubmittedRecordings"
            class="mr-4"
            label="Show submitted recordings"
            hide-details
          />
          <v-menu>
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
      <v-data-table
        v-model:items-per-page="itemsPerPage"
        :headers="headers"
        :items="myRecordingsDisplay"
        :custom-filter="tagFilter"
        filter-keys="['tag']"
        :search="filterTags.length ? 'seach-active' : ''"
        density="compact"
        :loading="dataLoading"
        class="elevation-1 my-recordings"
        :style="recordingListStyles"
      >
        <template #top>
          <div max-height="100px">
            <v-combobox
              v-model="filterTags"
              :items="recordingTags"
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
          <v-icon
            v-if="currentUserSubmission(item)"
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
        <template #bottom />
      </v-data-table>
      <div
        v-if="recordingList.length && configuration.mark_annotations_completed_enabled"
        class="d-flex justify-center align-center"
      >
        <v-progress-linear
          height="10"
          color="success"
          :model-value="submittedMyRecordings.length"
          min="0"
          :max="recordingList.length"
        />
        <span class="ml-4 text-h6">
          ({{ submittedMyRecordings.length }}/{{ recordingList.length }})
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
      <v-data-table
        v-model:items-per-page="itemsPerPage"
        :headers="sharedHeaders"
        :items="sharedRecordingsDisplay"
        :custom-filter="sharedTagFilter"
        filter-keys="['tag']"
        :search="sharedFilterTags.length ? 'seach-active' : ''"
        :loading="dataLoading"
        density="compact"
        class="elevation-1 shared-recordings"
        :style="recordingListStyles"
      >
        <template #top>
          <div max-height="100px">
            <v-combobox
              v-model="sharedFilterTags"
              :items="sharedRecordingTags"
              label="Filter recordings by tags"
              multiple
              chips
              closable-chips
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
          <v-icon
            v-if="currentUserSubmission(item)"
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
        <template #bottom />
      </v-data-table>
      <div
        v-if="sharedList.length && configuration.mark_annotations_completed_enabled"
        class="d-flex justify-center align-center"
      >
        <v-progress-linear
          height="10"
          color="success"
          :model-value="submittedSharedRecordings.length"
          min="0"
          :max="sharedList.length"
        />
        <span class="ml-4 text-h6">
          ({{ submittedSharedRecordings.length }}/{{ sharedList.length }})
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
