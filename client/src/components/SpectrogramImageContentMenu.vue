<script setup lang="ts">
import { ref, watch } from 'vue';
import useState from '@use/useState';

defineProps<{
  compressed: boolean;
  hasMaskUrls?: boolean;
}>();

const {
  contoursEnabled,
  imageOpacity,
  contourOpacity,
  contoursLoading,
  viewMaskOverlay,
  maskOverlayOpacity,
  setContoursEnabled,
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
    uncheckingImage.value = false;
  }
}

function onContourVisibilityChange(visible: boolean | null) {
  if (visible) {
    contourOpacity.value = lastContourOpacity.value ?? 1.0;
  } else {
    lastContourOpacity.value = contourOpacity.value;
    contourOpacity.value = 0;
    uncheckingContour.value = true;
  }
}

// Mask and contours are mutually exclusive
function onMaskOverlayChange(checked: boolean) {
  viewMaskOverlay.value = checked;
  if (checked) {
    setContoursEnabled(false);
  }
}

function onContoursEnabledChange(checked: boolean) {
  setContoursEnabled(checked);
  if (checked) {
    viewMaskOverlay.value = false;
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
    <v-menu
      location="top"
      :open-on-hover="false"
      :close-on-content-click="false"
      :close-delay="250"
    >
      <template #activator="{ props }">
        <v-icon
          v-if="!contoursLoading"
          v-tooltip:bottom="'Click to show overlay & contour options'"
          v-bind="props"
          size="25"
          :color="viewMaskOverlay || contoursEnabled ? 'blue' : ''"
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
          Overlay & Contour Options
        </v-card-title>
        <v-card-text>
          <!-- Show mask OR contours (mutually exclusive) -->
          <template v-if="hasMaskUrls">
            <div class="text-caption mb-2 d-flex align-center">
              <v-checkbox
                :model-value="viewMaskOverlay"
                :disabled="contoursEnabled"
                hide-details
                density="compact"
                class="mr-1 mt-0 flex-shrink-0"
                label="Show mask overlay"
                @update:model-value="onMaskOverlayChange($event === true)"
              />
            </div>
            <template v-if="viewMaskOverlay">
              <div class="text-caption mb-1">
                Mask opacity {{ (maskOverlayOpacity * 100).toFixed(0) }}%
              </div>
              <v-slider
                v-model="maskOverlayOpacity"
                :min="0.1"
                :max="1"
                :step="0.05"
                hide-details
                density="compact"
                class="mb-3"
              />
            </template>
          </template>

          <v-divider
            v-if="hasMaskUrls"
            class="my-2"
          />

          <!-- Show contours (with performance warning icon) -->
          <div class="text-caption mb-2 d-flex align-center">
            <v-checkbox
              :model-value="contoursEnabled"
              :disabled="viewMaskOverlay"
              hide-details
              density="compact"
              class="mr-1 mt-0 flex-shrink-0"
              label="Show contours"
              @update:model-value="onContoursEnabledChange($event === true)"
            />
            <v-tooltip location="top">
              <template #activator="{ props: tooltipProps }">
                <v-icon
                  v-bind="tooltipProps"
                  size="small"
                  color="warning"
                  class="ml-1"
                >
                  mdi-alert
                </v-icon>
              </template>
              <span>Contours may not be performant on large recordings.</span>
            </v-tooltip>
          </div>

          <!-- Image & contour opacity (only when contours enabled) -->
          <template v-if="contoursEnabled">
            <div class="text-caption mb-2 d-flex align-center">
              <v-checkbox
                :model-value="imageOpacity > 0"
                hide-details
                density="compact"
                class="mr-1 mt-0 flex-shrink-0"
                @update:model-value="onImageVisibilityChange"
              />
              Image opacity {{ (imageOpacity * 100).toFixed(2) }}%
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
              Contour opacity {{ (contourOpacity * 100).toFixed(2) }}%
            </div>
            <v-slider
              v-model="contourOpacity"
              :min="0"
              :max="1"
              :step="0.05"
              hide-details
              density="compact"
              class="mb-3"
            />
          </template>
        </v-card-text>
      </v-card>
    </v-menu>
  </div>
</template>
