<script lang="ts">
import {
  computed,
  defineComponent,
  ref,
  type Ref,
  onMounted,
  watch,
} from "vue";
import { deleteRecording, type Recording, getRecordingTags } from "../api/api";
import UploadRecording, {
  type EditingRecording,
} from "@components/UploadRecording.vue";
import useState from "@use/useState";
import BatchUploadRecording from "@components/BatchUploadRecording.vue";
import RecordingTable from "@components/RecordingTable.vue";
import RecordingLocationsMap from "@components/RecordingLocationsMap.vue";

export default defineComponent({
  components: {
    UploadRecording,
    BatchUploadRecording,
    RecordingTable,
    RecordingLocationsMap,
  },
  setup() {
    const {
      configuration,
      showSubmittedRecordings,
      recordingTagList,
      filterTags,
      sharedFilterTags,
      saveFilterTags,
      loadMapFilterBounds,
      saveMapFilterBounds,
      clearMapFilterBounds,
    } = useState();
    const showMap = ref(true);
    const filterListsByMap = ref(false);
    const mapBounds = ref<[number, number, number, number] | null>(null);
    const mapResizeTick = ref(0);
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

    // Restore the saved map bounds and enable "Filter lists to map" on load.
    const savedMapBounds = loadMapFilterBounds();
    if (savedMapBounds) {
      filterListsByMap.value = true;
      mapBounds.value = savedMapBounds;
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
        equipment: item.equipment || "",
        comments: item.comments || "",
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
        editingRecording.value["location"] = { lat, lon };
      }
      if (item.tags_text) {
        editingRecording.value.tags = item.tags_text.filter(
          (tag: string) => !!tag,
        );
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

    const showMyTable = computed(
      () =>
        configuration.value.is_admin ||
        configuration.value.non_admin_upload_enabled,
    );
    function setUnifiedTags(v: string[]) {
      filterTags.value = v;
      sharedFilterTags.value = v;
      saveFilterTags();
    }

    watch(showMap, (open) => {
      if (open) mapResizeTick.value += 1;
      else {
        filterListsByMap.value = false;
        mapBounds.value = null;
        clearMapFilterBounds();
      }
    });

    watch(filterListsByMap, (enabled) => {
      if (!enabled) {
        mapBounds.value = null;
        clearMapFilterBounds();
      }
    });

    const listBboxFilter = computed(
      (): [number, number, number, number] | null => {
        if (!showMap.value || !filterListsByMap.value) return null;
        return mapBounds.value;
      },
    );

    function onMapBounds(bounds: [number, number, number, number]) {
      mapBounds.value = bounds;
      // Only persist when filtering is enabled (bounds-change is only emitted then).
      if (filterListsByMap.value) {
        saveMapFilterBounds(bounds);
      }
    }

    return {
      configuration,
      showSubmittedRecordings,
      showMap,
      filterListsByMap,
      listBboxFilter,
      onMapBounds,
      showMyTable,
      mapResizeTick,
      mapBounds,
      filterTags,
      setUnifiedTags,
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
  <div class="recordings-scroll">
    <v-card class="mb-3">
      <v-card-title>
        <v-row>
          <div v-if="showMyTable">My Recordings</div>
          <v-spacer />
          <div class="d-flex justify-center align-center">
            <v-checkbox
              v-model="showSubmittedRecordings"
              class="mr-4"
              label="Show recordings with submitted annotations"
              hide-details
            />
            <v-switch
              v-model="showMap"
              class="mr-4"
              inset
              :color="showMap ? 'primary' : 'grey'"
              density="compact"
              label="Map"
              hide-details
            />
            <v-switch
              v-if="showMap"
              v-model="filterListsByMap"
              class="mr-4"
              inset
              :color="filterListsByMap ? 'primary' : 'grey'"
              density="compact"
              label="Filter lists to map"
              hide-details
            />
            <v-menu v-if="showMyTable">
              <template #activator="{ props }">
                <v-btn color="primary" v-bind="props">
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
    </v-card>

    <div class="recordings-layout" :class="{ 'with-map': showMap }">
      <div class="recordings-lists">
        <v-dialog v-model="deleteDialogOpen" width="auto">
          <v-card>
            <v-card-title class="pa-4">
              Delete {{ recordingToDelete?.name || "this recording" }}?
            </v-card-title>
            <v-card-actions class="pa-4">
              <v-btn variant="flat" @click="deleteDialogOpen = false">
                Cancel
              </v-btn>
              <v-btn variant="flat" color="error" @click="deleteOneRecording()">
                Delete
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-dialog>

        <v-card v-if="showMyTable">
          <v-card-text>
            <recording-table
              ref="myRecordingsTableRef"
              :class="{ 'my-files-with-map': showMap, 'my-files': !showMap }"
              variant="my"
              :tags="filterTags"
              :bbox-filter="listBboxFilter"
              :edit-recording="editRecording"
              :open-delete-recording-dialog="openDeleteRecordingDialog"
              @update:tags="setUnifiedTags"
            />
          </v-card-text>
        </v-card>

        <v-card
          :class="{
            'shared-with-my-files': showMap && showMyTable,
            'shared-dual-no-map': !showMap && showMyTable,
            'shared-alone-with-map': showMap && !showMyTable,
            'shared-alone': !showMap && !showMyTable,
          }"
        >
          <v-card-title>
            <v-row class="py-2">
              <div>Shared</div>
            </v-row>
          </v-card-title>
          <v-card-text>
            <recording-table
              variant="shared"
              :tags="filterTags"
              :bbox-filter="listBboxFilter"
              @update:tags="setUnifiedTags"
            />
          </v-card-text>
        </v-card>
      </div>

      <v-expand-x-transition>
        <v-card v-if="showMap" class="recordings-map-panel">
          <v-card-text class="pa-3 h-100">
            <RecordingLocationsMap
              class="map-right"
              height="100%"
              :tags="filterTags"
              :exclude-submitted="
                configuration.mark_annotations_completed_enabled &&
                !showSubmittedRecordings
              "
              :resize-tick="mapResizeTick"
              :report-bounds="showMap && filterListsByMap"
              :initial-bounds="mapBounds"
              @bounds-change="onMapBounds"
            />
          </v-card-text>
        </v-card>
      </v-expand-x-transition>
    </div>

    <v-dialog v-model="uploadDialog" width="700">
      <upload-recording
        :editing="editingRecording"
        @done="uploadDone()"
        @cancel="
          uploadDialog = false;
          editingRecording = null;
        "
      />
    </v-dialog>
    <v-dialog v-model="batchUploadDialog" width="700">
      <batch-upload-recording
        @done="uploadDone()"
        @cancel="
          batchUploadDialog = false;
          editingRecording = null;
        "
      />
    </v-dialog>
  </div>
</template>

<style scoped>
.recordings-scroll {
  max-height: calc(100vh - 64px);
  overflow-y: auto;
  padding-bottom: 16px;
}

.recordings-layout {
  display: block;
}

.recordings-layout.with-map {
  display: flex;
  align-items: stretch;
  gap: 12px;
}

.recordings-lists {
  flex: 1 1 auto;
  min-width: 0;
}

.recordings-map-panel {
  flex: 0 0 min(42vw, 680px);
  min-width: 360px;
  max-height: calc(100vh - 150px);
}

/* My recordings: classes are on <recording-table> (merged onto v-data-table root). */
:deep(.my-recordings.my-files) {
  height: calc(40vh - 64px);
  max-height: calc(40vh - 64px);
}

:deep(.my-recordings.my-files-with-map) {
  height: calc(45vh - 75px);
  max-height: calc(45vh - 75px);
}

/* Shared: layout classes are on the v-card; size the inner table. */
.shared-with-my-files :deep(.shared-recordings) {
  height: calc(45vh - 75px);
  max-height: calc(45vh - 75px);
}

.shared-dual-no-map :deep(.shared-recordings) {
  height: calc(90vh - 75px);
  max-height: calc(90vh - 75px);
}

.shared-alone-with-map :deep(.shared-recordings) {
  height: calc(85vh - 75px);
  max-height: calc(85vh - 75px);
}

.shared-alone :deep(.shared-recordings) {
  height: calc(90vh - 75px);
  max-height: calc(90vh - 75px);
}

.map-right {
  height: 100%;
  max-height: 100%;
}

:deep(.my-recordings),
:deep(.shared-recordings) {
  overflow-y: auto;
}

:deep(.my-recordings tr.current-recording-row),
:deep(.shared-recordings tr.current-recording-row) {
  border: 2px solid rgb(var(--v-theme-primary));
  box-sizing: border-box;
}
</style>
