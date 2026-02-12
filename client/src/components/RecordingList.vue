<script lang="ts">
import { defineComponent, ref, Ref, onMounted, computed, watch, CSSProperties } from 'vue';
import { FileAnnotation, getRecordings, Recording, Species, type RecordingListParams } from '../api/api';
import useState from '@use/useState';
import  { EditingRecording } from './UploadRecording.vue';

export default defineComponent({
  setup() {

    const {
      sharedList,
      recordingList,
      currentUser,
      configuration,
      showSubmittedRecordings,
      myRecordingsDisplay,
      sharedRecordingsDisplay,
    } = useState();
    const editingRecording: Ref<EditingRecording | null> = ref(null);

    // Only grab 20 recordings at a time to avoid loading all recordings at once.
    const buildListParams = (): RecordingListParams => {
      const excludeSubmitted = configuration.value.mark_annotations_completed_enabled
        && !showSubmittedRecordings.value;
      return {
        page: 1,
        limit: 20,
        sort_by: 'created',
        sort_direction: 'desc',
        ...(excludeSubmitted ? { exclude_submitted: true } : {}),
      };
    };

    const fetchRecordings = async () => {
      const params = buildListParams();
      const recordings = await getRecordings(false, params);
      recordingList.value = recordings.data.items;
      const shared = await getRecordings(true, { ...params, public: true });
      sharedList.value = shared.data.items;
    };
    onMounted(() => fetchRecordings());
    watch(showSubmittedRecordings, () => fetchRecordings());

    const openPanel = ref(1);
    const filtered = ref(true);
    const modifiedList = computed(() => {
      if (configuration.value.mark_annotations_completed_enabled) {
        return sharedRecordingsDisplay.value;
      }
      if (filtered.value) {
          return sharedList.value.filter((item) => !item.userMadeAnnotations);
      }
      return sharedList.value;
    });

    const userSubmittedAnnotation = (recording: Recording) => {
      const userSubmittedAnnotations = recording.fileAnnotations.filter((annotation: FileAnnotation) => (
        annotation.owner === currentUser.value && annotation.submitted
      ));
      if (userSubmittedAnnotations.length === 0 || userSubmittedAnnotations[0].species.length === 0) {
        return undefined;
      }
      return userSubmittedAnnotations[0].species.map((specie: Species) => specie.species_code).join(', ');
    };

    const styles = computed<CSSProperties>(() => {
      const appBarHeight = 64;
      const sidebarOptionsHeight = 36;
      const vettingOptionsHeight = 161;
      const showSubmittedHeight = 80;
      let offset = appBarHeight + sidebarOptionsHeight;
      if (configuration.value.mark_annotations_completed_enabled) {
        offset += (vettingOptionsHeight + showSubmittedHeight);
      }
      return {
        'max-height': `calc(100vh - ${offset}px)`,
        'overflow-y': 'auto'
      };
    });

    return {
      recordingList,
      sharedList,
      modifiedList,
      filtered,
      editingRecording,
      openPanel,
      userSubmittedAnnotation,
      configuration,
      myRecordingsDisplay,
      sharedRecordingsDisplay,
      showSubmittedRecordings,
      styles,
     };
  },
});
</script>

<template>
  <div>
    <v-row v-if="configuration.mark_annotations_completed_enabled">
      <v-col>
        <v-checkbox
          v-model="showSubmittedRecordings"
          label="Show submitted recordings"
          hide-details
        />
      </v-col>
    </v-row>
    <v-expansion-panels
      v-model="openPanel"
      :style="styles"
    >
      <v-expansion-panel v-if="configuration.is_admin || configuration.non_admin_upload_enabled">
        <v-expansion-panel-title>My Recordings</v-expansion-panel-title>
        <v-expansion-panel-text>
          <div
            v-for="item in myRecordingsDisplay"
            :key="`public_${item.id}`"
          >
            <v-card class="pa-2 my-2">
              <v-row dense>
                <v-col class="text-left">
                  <b>Name:</b><router-link
                    :to="`/recording/${item.id.toString()}/spectrogram`"
                  >
                    {{ item.name }}
                  </router-link>
                </v-col>
              </v-row>
              <v-row dense>
                <v-col>
                  <b>Public:</b>
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
                </v-col>
                <v-col>
                  <div>
                    <b class="pr-1">Annotations:</b>{{ item.userAnnotations }}
                  </div>
                </v-col>
              </v-row>
              <v-row
                v-if="configuration.mark_annotations_completed_enabled && userSubmittedAnnotation(item)"
                dense
              >
                <v-col>
                  <div>
                    <b>Submitted: </b>
                    <v-icon
                      v-if="userSubmittedAnnotation(item)"
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
                  </div>
                </v-col>
                <v-col v-if="userSubmittedAnnotation(item)">
                  <b>My label: </b>
                  <span>{{ userSubmittedAnnotation(item) }}</span>
                </v-col>
              </v-row>
            </v-card>
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel>
        <v-expansion-panel-title>Public</v-expansion-panel-title>
        <v-expansion-panel-text class="ma-0 pa-0">
          <v-switch
            v-if="!configuration.mark_annotations_completed_enabled"
            v-model="filtered"
            label="Filter Annotated"
            dense
          />
          <div
            v-for="item in modifiedList"
            :key="`public_${item.id}`"
          >
            <v-card class="pa-2 my-2">
              <v-row dense>
                <v-col class="text-left">
                  <b class="pr-1">Name:</b>
                  <router-link
                    :to="`/recording/${item.id.toString()}/spectrogram`"
                  >
                    {{ item.name }}
                  </router-link>
                </v-col>
              </v-row>
              <v-row dense>
                <v-col>
                  <div style="font-size:0.75em">
                    <b>Owner:</b> {{ item.owner_username }}
                  </div>
                </v-col>
              </v-row>
              <v-row dense>
                <v-col v-if="!configuration.mark_annotations_completed_enabled">
                  <div>
                    <b>Annotated:</b>
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
                  </div>
                </v-col>
                <v-col v-else>
                  <div>
                    <b>Submitted: </b>
                    <v-icon
                      v-if="userSubmittedAnnotation(item)"
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
                  </div>
                </v-col>
                <v-col
                  v-if="configuration.mark_annotations_completed_enabled && userSubmittedAnnotation(item)"
                >
                  <b>My label: </b>
                  <span>{{ userSubmittedAnnotation(item) }}</span>
                </v-col>
              </v-row>
            </v-card>
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </div>
</template>

<style scoped>
.v-expansion-panel-text>>> .v-expansion-panel-text__wrap {
  padding: 0 !important;
}

.v-expansion-panel-text__wrapper {
    padding: 0 !important;
}

.overflow-recordings {
  max-height: 50vh;
  overflow-y: auto;
}
</style>
