<script setup lang="ts">
import { ref } from "vue";
import useState from "@use/useState";

defineProps<{
  compressed: boolean;
  hasMaskUrls?: boolean;
}>();

const { viewMaskOverlay, maskOverlayOpacity } = useState();

const hover = ref(false);

function onMaskOverlayChange(checked: boolean) {
  viewMaskOverlay.value = checked;
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
      :open-on-hover="true"
      :open-delay="200"
      :close-on-content-click="false"
      :close-delay="250"
    >
      <template #activator="{ props }">
        <v-icon v-bind="props" size="25" :color="viewMaskOverlay ? 'blue' : ''">
          mdi-vector-curve
        </v-icon>
      </template>
      <v-card min-width="300" class="pa-3">
        <v-card-title class="text-subtitle-1">
          Mask Overlay Options
        </v-card-title>
        <v-card-text>
          <template v-if="hasMaskUrls">
            <div class="text-caption mb-2 d-flex align-center">
              <v-checkbox
                :model-value="viewMaskOverlay"
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
        </v-card-text>
      </v-card>
    </v-menu>
  </div>
</template>
