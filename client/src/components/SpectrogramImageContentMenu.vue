<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import useState from '@use/useState';

defineProps<{
  compressed: boolean;
}>();

const {
  contoursEnabled,
  imageOpacity,
  contourOpacity,
  contoursLoading,
  toggleContoursEnabled,
} = useState();

const hover = ref(false);

// When unchecked via checkbox we save the value to restore on check.
// When opacity is slid to 0 we clear these so that checking restores to 1.0.
const lastImageOpacity = ref<number | undefined>(undefined);
const lastContourOpacity = ref<number | undefined>(undefined);
const uncheckingImage = ref(false);
const uncheckingContour = ref(false);

watch(imageOpacity, (newVal) => {
  if (newVal === 0 && !uncheckingImage.value) {
    lastImageOpacity.value = undefined;
  }
});
watch(contourOpacity, (newVal) => {
  if (newVal === 0 && !uncheckingContour.value) {
    lastContourOpacity.value = undefined;
  }
});

function onImageVisibilityChange(visible: boolean | null) {
  if (visible) {
    imageOpacity.value = lastImageOpacity.value ?? 1.0;
  } else {
    lastImageOpacity.value = imageOpacity.value;
    imageOpacity.value = 0;
    uncheckingImage.value = true;
    nextTick(() => {
      uncheckingImage.value = false;
    });
  }
}

function onContourVisibilityChange(visible: boolean | null) {
  if (visible) {
    contourOpacity.value = lastContourOpacity.value ?? 1.0;
  } else {
    lastContourOpacity.value = contourOpacity.value;
    contourOpacity.value = 0;
    uncheckingContour.value = true;
    nextTick(() => {
      uncheckingContour.value = false;
    });
  }
}
</script>

<template>
  <div
    v-if="compressed"
    class="d-flex flex-column align-center"
    @mouseenter="hover = true"
    @mouseleave="hover = false"
  >
    <v-icon 
      v-if="!contoursLoading && !contoursEnabled"
      v-tooltip:bottom="'Click to show contour display options'"
      size="25"
      :color="contoursEnabled ? 'blue' : ''"
      @click="toggleContoursEnabled()"
    >
      mdi-vector-curve
    </v-icon>
    <v-progress-circular
      v-else-if="contoursLoading"
      indeterminate
      size="25"
      color="primary"
    />
    <v-menu
      v-else
      location="top"
      :open-on-hover="true"
      :close-on-content-click="false"
      :close-delay="250"
    >
      <template #activator="{ props }">
        <v-icon
          v-if="!contoursLoading"
          v-bind="props"
          size="25"
          :color="contoursEnabled ? 'blue' : ''"
          @click.prevent="toggleContoursEnabled()"
        >
          mdi-vector-curve
        </v-icon>
        <v-progress-circular
          v-else
          indeterminate
          size="25"
          color="primary"
        />
      </template>
      <v-card
        min-width="300"
        class="pa-3"
      >
        <v-card-title class="text-subtitle-1">
          Contour Display Options
        </v-card-title>
        <v-card-text>
          <div class="text-caption mb-2 d-flex align-center">
            <v-checkbox
              :model-value="imageOpacity > 0"
              hide-details
              density="compact"
              class="mr-1 mt-0 flex-shrink-0"
              @update:model-value="onImageVisibilityChange"
            />
            Image opacity {{ (imageOpacity*100).toFixed(2) }}%
          </div>
          <v-slider
            v-model="imageOpacity"
            :min="0"
            :max="1"
            :step="0.05"
            hide-details
            density="compact"
            class="mb-2"
          />
          <div class="text-caption mb-2 d-flex align-center">
            <v-checkbox
              :model-value="contourOpacity > 0"
              hide-details
              density="compact"
              class="mr-1 mt-0 flex-shrink-0"
              @update:model-value="onContourVisibilityChange"
            />
            Contour opacity {{ (contourOpacity*100).toFixed(2) }}%
          </div>
          <v-slider
            v-model="contourOpacity"
            :min="0"
            :max="1"
            :step="0.05"
            hide-details
            density="compact"
          />
        </v-card-text>
      </v-card>
    </v-menu>
  </div>
</template>
