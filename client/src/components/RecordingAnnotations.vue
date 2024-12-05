<script lang="ts">
import { defineComponent, onMounted, PropType, Ref } from "vue";
import { SpectroInfo } from './geoJS/geoJSUtils';
import useState from "../use/useState";
import { watch, ref } from "vue";
import AnnotationEditor from "./AnnotationEditor.vue";
import { FileAnnotation, getFileAnnotations, putFileAnnotation, Species, SpectrogramAnnotation, SpectrogramTemporalAnnotation, UpdateFileAnnotation } from "../api/api";
import RecordingAnnotationEditor from "./RecordingAnnotationEditor.vue";
export default defineComponent({
  name: "AnnotationList",
  components: {
    RecordingAnnotationEditor,
  },
  props: {
    species: {
      type: Array as PropType<Species[]>,
      required: true,
    },
    recordingId: {
      type: Number,
      required: true,
    }
  },
  emits: [],
  setup(props) {
    const selectedAnnotation: Ref<null | FileAnnotation> = ref(null);
    const annotationState: Ref<'creating' | 'editing' | null> = ref(null);
    const annotations: Ref<FileAnnotation[]> = ref([]);

    const setSelectedId = (annotation: FileAnnotation) => {
      selectedAnnotation.value = annotation;
    };

    const loadFileAnnotations = async () => {
      annotations.value = (await getFileAnnotations(props.recordingId)).data;
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

    return {
      selectedAnnotation,
      annotationState,
      annotations,
      setSelectedId,
      addAnnotation,
      updatedAnnotation,
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
      <v-col>
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
            <span>{{ annotation.owner }}</span>
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
