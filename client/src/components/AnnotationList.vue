<script lang="ts">
import { defineComponent, PropType } from "vue";
import { SpectroInfo } from './geoJS/geoJSUtils';
import { SpectrogramAnnotation } from "../api/api";
import useState from "../use/useState";

export default defineComponent({
  name: "AnnotationList",
  components: {
  },
  props: {
    spectroInfo: {
      type: Object as PropType<SpectroInfo | undefined>,
      default: () => undefined,
    },
    annotations: {
      type: Array as PropType<SpectrogramAnnotation[]>,
      default: () => [],
    },
    selectedId: {
        type: Number as PropType<number | null>,
        default: null,
    }
  },
  emits: ['select'],
  setup() {
    const { annotationState, setAnnotationState } = useState();
    return {
        annotationState,
        setAnnotationState,
    };
  },
});
</script>

<template>
  <v-card class="pa-0 ma-0">
    <v-card-title>
      <v-row class="pa-2">
        Annotations
        <v-spacer />
        <v-btn
          :disabled="annotationState === 'creating'"
          @click="annotationState = 'creating'"
        >
          Add<v-icon>mdi-plus</v-icon>
        </v-btn>
      </v-row>
    </v-card-title>
    <v-list>
      <v-list-item
        v-for="annotation in annotations"
        :key="annotation.id"
        :class="{selected: annotation.id===selectedId}"
        class="d-flex flex-column align-start"
        @click="$emit('select', annotation.id)"
      >
        <v-row>
          <v-col
            class="annotation-id"
          >
            {{ annotation.id }}
          </v-col>
          <v-col class="annotation-time">
            <span>{{ annotation.start_time }}ms to {{ annotation.end_time }}ms </span>
          </v-col>
          <v-col class="annotation-freq">
            <span>{{ annotation.low_freq }}hz to {{ annotation.high_freq }}hz </span>
          </v-col>
        </v-row>
        <v-row
          v-for="item in annotation.species"
          :key="`${annotation.id}_${item.common_name}`"
        >
          <v-col>
            <div class="species-name">
              {{ item.common_name }}
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
  </v-card>
</template>

<style lang="scss" scoped>
.annotation-id {
    cursor:pointer;
    text-decoration: underline;
}
.annotation-time {
    font-size: 0.7em;
}
.annotation-freq {
    font-size: 0.7em;
}
.species-name {
    font-weight: bold;
    font-size: 0.7em;
}
.species-hierarchy {
    font-size: 0.5em;
}
.selected {
    background-color: cyan;
}
</style>
