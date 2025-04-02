<script lang="ts">
import { defineComponent, onMounted, PropType, Ref } from "vue";
import { ref } from "vue";
import { FileAnnotation, getFileAnnotations, putFileAnnotation, Species, UpdateFileAnnotation } from "../api/api";
import RecordingAnnotationEditor from "./RecordingAnnotationEditor.vue";
import { getNABatRecordingFileAnnotations } from "../api/NABatApi";
import RecordingAnnotationDetails from "./RecordingAnnotationDetails.vue";
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
    }
  },
  emits: [],
  setup(props) {
    const selectedAnnotation: Ref<null | FileAnnotation> = ref(null);
    const annotationState: Ref<'creating' | 'editing' | null> = ref(null);
    const annotations: Ref<FileAnnotation[]> = ref([]);
    const detailsDialog = ref(false);
    const detailRecordingId = ref(-1);

    const setSelectedId = (annotation: FileAnnotation) => {
      if (!props.type) {
        selectedAnnotation.value = annotation;
      }
    };

    const loadFileAnnotations = async () => {
      if (props.type === 'nabat') {
        annotations.value = (await getNABatRecordingFileAnnotations(props.recordingId)).data;
      } else {
        annotations.value = (await getFileAnnotations(props.recordingId)).data;
      }
    };

    onMounted(() => loadFileAnnotations());

    const addAnnotation = async () => {
      const newAnnotation: UpdateFileAnnotation = {
        recordingId: props.recordingId,
        species: [],
        comments: '',
        model: 'User Defined',
        confidence: 1.0,

      };
      await putFileAnnotation(newAnnotation);
      await loadFileAnnotations();
      if (annotations.value.length) {
        setSelectedId(annotations.value[annotations.value.length - 1]);
      }
    };

    const updatedAnnotation = async (deleted = false) => {
      annotations.value = (await getFileAnnotations(props.recordingId)).data;
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

    const loadDetails = async (id: number) => {
      detailRecordingId.value = id;
      detailsDialog.value = true;
    };

    return {
      selectedAnnotation,
      annotationState,
      annotations,
      setSelectedId,
      addAnnotation,
      updatedAnnotation,
      loadDetails,
      detailsDialog,
      detailRecordingId,
    };
  },
});
</script>

<template>
  <div>
    <v-row class="pa-2">
      <v-col>
        Annotations
      </v-col>
      <v-spacer />
      <v-col v-if="!type">
        <v-btn
          :disabled="annotationState === 'creating'"
          @click="addAnnotation()"
        >
          Add<v-icon>mdi-plus</v-icon>
        </v-btn>
      </v-col>
    </v-row>

    <v-list>
      <v-list-item
        v-for="annotation in annotations"
        :id="`annotation-${annotation.id}`"
        :key="annotation.id"
        :class="{ selected: annotation.id === selectedAnnotation?.id }"
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
            <span>{{ annotation.confidence }} </span>
          </v-col>
          <v-col class="annotation-model">
            <span>{{ annotation.model }} </span>
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
      class="mt-4"
      @update:annotation="updatedAnnotation()"
      @delete:annotation="updatedAnnotation(true)"
    />
    <v-dialog
      v-model="detailsDialog"
      width="600"
    >
      <RecordingAnnotationDetails
        :recording-id="detailRecordingId"
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
  max-height: 60vh;
  overflow-y: auto;
}

.recording-list {
  max-height: 85vh;
  overflow-y: auto;
}
</style>
