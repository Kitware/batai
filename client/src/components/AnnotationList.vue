<script lang="ts">
import { computed, defineComponent, PropType, ref, Ref, watch } from "vue";
import { SpectroInfo, useGeoJS } from './geoJS/geoJSUtils';
import { Species, SpectrogramAnnotation } from "../api/api";

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
  setup(props) {
    return {
    };
  },
});
</script>

<template>
  <v-card class="pa-0 ma-0">
    <v-card-title>Annotations</v-card-title>
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
