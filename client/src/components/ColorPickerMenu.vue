<script setup lang="ts">
import * as d3 from 'd3';
import { defineModel, ref } from 'vue';
defineProps({
  tooltipText: {
    type: String,
    default: ''
  },
});
const colorpickerMenu = ref(false);
const color = defineModel({ default: 'rgb(0, 0, 0)'});
function updateColor(colorVal: string) {
  if (!colorVal.includes(',')) {
    // convert rgb(0 0 0) to rgb(0, 0, 0)
    colorVal = colorVal.replace(/rgb\((\d+)\s+(\d+)\s+(\d+)\)/, 'rgb($1, $2, $3)');
  }
  const d3Color = d3.color(colorVal);
  if (d3Color) {
    color.value = d3Color.formatRgb();
  }
}
</script>

<template>
  <v-menu
    v-model="colorpickerMenu"
    :close-on-content-click="false"
    offset-y
  >
    <template #activator="{ props: subProps }">
      <v-tooltip :text="tooltipText">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            v-bind="{ ...subProps, ...tooltipProps }"
            :style="{ backgroundColor: color }"
            class="color-square mx-2 mt-4"
          />
        </template>
      </v-tooltip>
    </template>
    <v-card>
      <v-card-text>
        <v-color-picker
          v-model="color"
          mode="rgb"
          elevation="0"
          @update:model-value="updateColor"
        />
      </v-card-text>
    </v-card>
  </v-menu>
</template>

<style scoped>
.color-square {
  width: 32px;
  height: 32px;
  min-width: 32px;
  border-radius: 4px;
}
</style>
