<script lang="ts">
import { defineComponent, PropType } from "vue";
import { SpectroInfo } from './geoJS/geoJSUtils';
import useState from "../use/useState";
import { watch, ref } from "vue";
import AnnotationEditor from "./AnnotationEditor.vue";
import { Species, SpectrogramAnnotation, SpectrogramTemporalAnnotation } from "../api/api";
import RecordingAnnotations from "./RecordingAnnotations.vue";
export default defineComponent({
  name: "AnnotationList",
  components: {
    AnnotationEditor,
    RecordingAnnotations,
  },
  props: {
    spectroInfo: {
      type: Object as PropType<SpectroInfo | undefined>,
      default: () => undefined,
    },
    selectedAnnotation: {
      type: Object as PropType<SpectrogramAnnotation | SpectrogramTemporalAnnotation | null>,
      default: () => null,
    },
    species: {
        type: Array as PropType<Species[]>,
        required: true,
    },
    recordingId: {
        type: String,
        required: true,
    }
  },
  emits: ['select', 'update:annotation', 'delete:annotation'],
  setup() {
    const { creationType, annotationState, setAnnotationState, annotations, temporalAnnotations, selectedId, selectedType, setSelectedId, sideTab } = useState();
    const tab = ref('recording');
    const scrollToId = (id: number) => {
    const el = document.getElementById(`annotation-${id}`);
    if (el) {
      el.scrollIntoView({block: 'end', behavior: 'smooth'});
    }
  };
  watch(selectedId, () => {
    tab.value = selectedType.value;
    if (selectedId.value !== null) {
      scrollToId(selectedId.value);
    }
  });
  watch(selectedType, () => {
    tab.value = selectedType.value;
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tabSwitch = (event: any) => {
    // On tab switches we want to deselect the curret annotation
    if (['sequence', 'pulse'].includes(event)) {
      tab.value = event as 'sequence' | 'pulse';
      selectedType.value = event as 'sequence' | 'pulse';
      selectedId.value = null;
    } else {
      tab.value = 'recording';
    }
  };

    return {
        annotationState,
        annotations,
        creationType,
        temporalAnnotations,
        selectedId,
        selectedType,
        setAnnotationState,
        setSelectedId,
        tabSwitch,
        tab,
        sideTab,
    };
  },
});
</script>

<template>
  <div
    class="pa-2"
    :class="{'annotation-list': ['pulse','sequence'].includes(tab),'recording-list': !['pulse','sequence'].includes(tab)}"
  >
    <v-row dense>
      <v-tabs
        v-model="tab"
        class="ma-auto"
        @update:model-value="tabSwitch($event)"
      >
        <v-tooltip
          location="bottom"
          open-delay="400"
        >
          <template #activator="{ props }">
            <v-tab
              value="recording"
              size="x-small"
              v-bind="props"
            >
              Recording
            </v-tab>
          </template>
          <span>Recording/File Level Species Annotations</span>
        </v-tooltip>
        <v-tooltip
          location="bottom"
          open-delay="400"
        >
          <template #activator="{ props }">
            <v-tab
              value="sequence"
              size="x-small"
              v-bind="props"
            >
              Sequence
            </v-tab>
          </template>
          <span>Sequence Level annotations (Approach/Search/Terminal/Social)</span>
        </v-tooltip>
        <v-tooltip
          location="bottom"
          open-delay="400"
        >
          <template #activator="{ props }">
            <v-tab
              value="pulse"
              size="x-small"
              v-bind="props"
            >
              Pulse
            </v-tab>
          </template>
          <span>Pulse Level Annotations (for a single pulse)</span>
        </v-tooltip>
      </v-tabs>
    </v-row>
    <v-window v-model="tab">
      <v-window-item value="pulse">
        <v-row class="pa-2">
          <v-col>
            Annotations
          </v-col>
          <v-spacer />
          <v-col>
            <v-btn
              :disabled="annotationState === 'creating'"
              @click="annotationState = 'creating'; creationType = 'pulse' "
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
            :class="{selected: annotation.id===selectedId}"
            class="annotation-item"
            @click="setSelectedId(annotation.id, 'pulse')"
          >
            <v-row>
              <v-col class="annotation-time">
                <span>{{ annotation.start_time }}-{{ annotation.end_time }}ms</span>
                <span class="pl-2"><b>({{ annotation.end_time - annotation.start_time }}ms)</b></span>
              </v-col>
              <v-col class="annotation-freq">
                <span>{{ (annotation.low_freq/1000).toFixed(1) }}-{{ (annotation.high_freq/1000).toFixed() }}Khz </span>
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
      </v-window-item>
      <v-window-item value="sequence">
        <v-row class="pa-2">
          <v-col>
            Annotations
          </v-col>
          <v-spacer />
          <v-col>
            <v-btn
              :disabled="annotationState === 'creating'"
              @click="annotationState = 'creating'; creationType = 'sequence' "
            >
              Add<v-icon>mdi-plus</v-icon>
            </v-btn>
          </v-col>
        </v-row>

        <v-list>
          <v-list-item
            v-for="annotation in temporalAnnotations"
            :id="`annotation-${annotation.id}`"
            :key="annotation.id"
            :class="{selected: annotation.id===selectedId}"
            class="annotation-item"
            @click="setSelectedId(annotation.id, 'sequence')"
          >
            <v-row>
              <v-col class="annotation-time">
                <span>{{ annotation.start_time }}-{{ annotation.end_time }}ms</span>
                <span class="pl-2"><b>({{ annotation.end_time - annotation.start_time }}ms)</b></span>
              </v-col>
              <v-col class="annotation-time">
                <b>Type:</b><span>{{ annotation.type }}</span>
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
      </v-window-item>
      <v-window-item value="recording">
        <RecordingAnnotations 
          :species="species"
          :recording-id="parseInt(recordingId)"
        />
      </v-window-item>
      <annotation-editor
        v-if="selectedAnnotation && ['pulse', 'sequence'].includes(tab)"
        :species="species"
        :recording-id="recordingId"
        :annotation="selectedAnnotation"
        class="mt-4"
        @update:annotation="$emit('update:annotation')"
        @delete:annotation="$emit('delete:annotation')"
      />
    </v-window>
  </div>
</template>

<style lang="scss" scoped>
.annotation-id {
    cursor:pointer;
    text-decoration: underline;
}
.annotation-time {
    font-size: 1em;
}
.annotation-freq {
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
