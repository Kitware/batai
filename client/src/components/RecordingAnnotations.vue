<script lang="ts">
import { computed, defineComponent, onMounted, PropType, Ref, watch } from "vue";
import { ref } from "vue";
import { FileAnnotation, getFileAnnotations, putFileAnnotation, Species, UpdateFileAnnotation } from "@api/api";
import RecordingAnnotationEditor from "./RecordingAnnotationEditor.vue";
import { getNABatRecordingFileAnnotations, putNABatFileAnnotation } from "@api/NABatApi";
import RecordingAnnotationDetails from "./RecordingAnnotationDetails.vue";
import useState from "@use/useState";
import { decodeJWT } from "../use/useJWTToken";
export default defineComponent({
  name: "AnnotationList",
  components: {
    RecordingAnnotationEditor,
    RecordingAnnotationDetails,
  },
  props: {
    species: {
      type: Array as PropType<Species[]>,
      required: true,
    },
    recordingId: {
      type: Number,
      required: true,
    },
    type: {
      type: String as PropType<'nabat' | null>,
      default: () => null,
    },
    apiToken: {
      type: String,
      default: () => '',
    },
  },
  emits: [],
  setup(props) {
    const selectedAnnotation: Ref<null | FileAnnotation> = ref(null);
    const annotationState: Ref<'creating' | 'editing' | null> = ref(null);
    const annotations: Ref<FileAnnotation[]> = ref([]);
    const detailsDialog = ref(false);
    const detailRecordingId = ref(-1);
    const { configuration, isNaBat, currentUser, markAnnotationSubmitted } = useState();

    const setSelectedId = (annotation: FileAnnotation) => {
      selectedAnnotation.value = annotation;
    };

    const currentNaBatUser: Ref<string | null> = ref(null);



    const loadFileAnnotations = async () => {
      if (props.type === 'nabat') {
        annotations.value = (await getNABatRecordingFileAnnotations(props.recordingId, props.apiToken)).data;
      } else {
        annotations.value = (await getFileAnnotations(props.recordingId)).data;
      }
    };

    watch(() => props.recordingId, async () => {
      selectedAnnotation.value = null;
      await loadFileAnnotations();
    });

    onMounted(async () => {
      await loadFileAnnotations();
      if (props.type  === 'nabat') {
        const decoded = decodeJWT(props.apiToken);
        if (decoded['email']) {
          currentNaBatUser.value = decoded['email'];
          const foundItem = annotations.value.find((item) => item.owner === currentNaBatUser.value);
          if (foundItem) {
            setSelectedId(foundItem);
          }
        }
      }
    });

    const addAnnotation = async () => {
      const newAnnotation: UpdateFileAnnotation & { apiToken?: string } = {
        recordingId: props.recordingId,
        species: [],
        comments: '',
        model: 'User Defined',
        confidence: 1.0,
        apiToken: props.apiToken,

      };
      props.type === 'nabat' ? await putNABatFileAnnotation(newAnnotation) : await putFileAnnotation(newAnnotation);
      await loadFileAnnotations();
      if (annotations.value.length) {
        setSelectedId(annotations.value[annotations.value.length - 1]);
      }
    };

    const updatedAnnotation = async (deleted = false) => {
      await loadFileAnnotations();
      if (selectedAnnotation.value) {
        const found = annotations.value.find((item) => selectedAnnotation.value?.id === item.id);
        if (found) {
          selectedAnnotation.value = found;
        }
      }
      if (deleted) {
        selectedAnnotation.value = null;
      }
    };

    function handleSubmitAnnotation(annotation: FileAnnotation, submitSuccess: boolean) {
      if (submitSuccess) {
        annotation.submitted = true;
        // Also update submitted status on the recording object
        // This forces recomputation of allRecordings
        markAnnotationSubmitted(props.recordingId, annotation.id);
      }
    }

    const loadDetails = async (id: number) => {
      detailRecordingId.value = id;
      detailsDialog.value = true;
    };

    const isAdmin = computed(() => configuration.value.is_admin);

    const userSubmittedAnnotationId = computed(() => {
      if (!configuration.value.mark_annotations_completed_enabled) {
        return undefined;
      }
      const userAnnotations = annotations.value.filter((annotation: FileAnnotation) => annotation.owner === currentUser.value);
      const submittedAnnotation = userAnnotations.find((annotation: FileAnnotation) => annotation.submitted);
      return submittedAnnotation?.id;
    });

    const disableNaBatAnnotations = computed(() => {
      const currentUserAnnotations = annotations.value.filter((item) => item.owner === currentNaBatUser.value);
      if (isAdmin.value && props.type === 'nabat' && !props.apiToken) {
        return true;
      }
      return ( currentUserAnnotations.length > 0 && props.type === 'nabat');
    });

    function getConfidenceLabelText(confidence: number) {
      return `Confidence: ${confidence.toFixed(2)}`;
    }

    return {
      selectedAnnotation,
      annotationState,
      annotations,
      setSelectedId,
      addAnnotation,
      updatedAnnotation,
      loadDetails,
      getConfidenceLabelText,
      isNaBat,
      detailsDialog,
      detailRecordingId,
      disableNaBatAnnotations,
      currentNaBatUser,
      userSubmittedAnnotationId,
      handleSubmitAnnotation,
    };
  },
});
</script>

<template>
  <div>
    <v-row class="pa-4">
      <v-col
        v-if="!isNaBat()"
        cols="6"
      >
        <v-row>
          Annotations
        </v-row>
        <v-row
          v-if="userSubmittedAnnotationId"
          class="mt-8"
        >
          <b>File Reviewed</b>
          <v-icon color="success">
            mdi-check
          </v-icon>
        </v-row>
      </v-col>
      <v-spacer />
      <v-col v-if="!isNaBat() || !disableNaBatAnnotations">
        <v-btn
          :disabled="annotationState === 'creating' || disableNaBatAnnotations"
          @click="addAnnotation()"
        >
          Add<v-icon>mdi-plus</v-icon>
        </v-btn>
      </v-col>
    </v-row>

    <v-list class="annotation-list">
      <v-list-item
        v-for="annotation in annotations"
        :id="`annotation-${annotation.id}`"
        :key="annotation.id"
        :class="{ selected: annotation.id === selectedAnnotation?.id }"
        :disabled="type === 'nabat' && disableNaBatAnnotations && annotation.owner !== currentNaBatUser"
        class="annotation-item"
        @click="setSelectedId(annotation)"
      >
        <v-row>
          <v-col class="annotation-owner">
            <div>{{ annotation.owner }}</div>
            <v-btn
              v-if="annotation.hasDetails"
              size="small"
              @click.stop.prevent="loadDetails(annotation.id)"
            >
              Details
            </v-btn>
          </v-col>
          <v-col class="annotation-confidence">
            <span>{{ getConfidenceLabelText(annotation.confidence) }} </span>
          </v-col>
          <v-col class="annotation-model">
            <span>{{ annotation.model }} </span>
          </v-col>
          <v-col v-if="annotation.submitted">
            Submitted
            <v-icon color="success">
              mdi-check
            </v-icon>
          </v-col>
        </v-row>
        <v-row
          v-for="item in annotation.species"
          :key="`${annotation.id}_${item.common_name}`"
          class="ma-0 pa-0"
        >
          <v-col class="ma-0 pa-0">
            <div class="species-name">
              {{ item.species_code || item.common_name }}
            </div>
            <div
              v-if="item.family"
              class="species-hierarchy"
            >
              <span> {{ item.family }}</span>
              <span v-if="item.genus">-></span>
              <span v-if="item.genus">{{ item.genus }}</span>
            </div>
          </v-col>
        </v-row>
      </v-list-item>
    </v-list>
    <RecordingAnnotationEditor
      v-if="selectedAnnotation"
      :species="species"
      :recording-id="recordingId"
      :annotation="selectedAnnotation"
      :api-token="apiToken"
      :submitted-annotation-id="userSubmittedAnnotationId"
      :type="type"
      class="mt-4"
      @update:annotation="updatedAnnotation()"
      @delete:annotation="updatedAnnotation(true)"
      @submit:annotation="handleSubmitAnnotation"
    />
    <v-dialog
      v-model="detailsDialog"
      width="600"
    >
      <RecordingAnnotationDetails
        :recording-id="detailRecordingId"
        :api-token="apiToken"
        @close="detailsDialog = false"
      />
    </v-dialog>
  </div>
</template>

<style lang="scss" scoped>
.annotation-id {
  cursor: pointer;
  text-decoration: underline;
}

.annotation-owner {
  font-size: 1em;
}

.annotation-confidence {
  font-size: 1em;
}

.annotation-model {
  font-size: 1em;
}

.annotation-item {
  border: 1px solid gray;
}

.species-name {
  font-weight: bold;
  font-size: 1em;
}

.species-hierarchy {
  font-size: 0.75em;
}

.selected {
  background-color: cyan;
}

.annotation-list {
  max-height: 85vh;
  overflow-y: auto;
}

.recording-list {
  max-height: 85vh;
  overflow-y: auto;
}
</style>
