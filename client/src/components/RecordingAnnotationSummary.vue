<script lang="ts">
import { defineComponent, PropType } from "vue";
import { FileAnnotation } from "../api/api";
export default defineComponent({
  name: "AnnotationList",
  components: {
  },
  props: {
    fileAnnotations: {
      type: Array as PropType<FileAnnotation[]>,
      required: true,
    },
  },
  emits: [],
  setup() {

    return {
    };
  },
});
</script>

<template>
  <v-tooltip
    v-if="fileAnnotations.length"
    min-width="500"
  >
    <template #activator="{ props: subProps }">
      <span>{{ fileAnnotations.length }} Annotations <v-icon v-bind="subProps">mdi-information-outline</v-icon></span>
    </template>
    <v-card>
      <v-list>
        <v-list-item
          v-for="annotation in fileAnnotations"
          :key="`${annotation.id}`"
          class="annotation-item "
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
    </v-card>
  </v-tooltip>
  <span v-else>
    None
  </span>
</template>

<style lang="scss" scoped>

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
</style>
