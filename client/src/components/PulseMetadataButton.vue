<script lang="ts">
import { defineComponent, ref } from "vue";
import usePulseMetadata from "@use/usePulseMetadata";

export default defineComponent({
  name: "PulseMetadataButton",
  props: {
    recordingId: {
      type: [String, Number],
      default: null,
    },
    compressed: {
      type: Boolean,
      default: false,
    },
  },
  setup(props) {
    const colorsExpanded = ref<number | undefined>(undefined);
    const {
      viewPulseMetadataLayer,
      toggleViewPulseMetadataLayer,
      loadPulseMetadata,
      pulseMetadataList,
      pulseMetadataLoading,
      pulseMetadataLineColor,
      pulseMetadataLineSize,
      pulseMetadataHeelColor,
      pulseMetadataCharFreqColor,
      pulseMetadataKneeColor,
      pulseMetadataPointSize,
      pulseMetadataShowLabels,
      pulseMetadataDurationFreqLineColor,
    } = usePulseMetadata();

    const togglePulseMetadata = async () => {
      if (pulseMetadataList.value.length === 0 && props.recordingId != null) {
        await loadPulseMetadata(Number(props.recordingId));
      }
      toggleViewPulseMetadataLayer();
    };

    return {
      pulseMetadataLoading,
      viewPulseMetadataLayer,
      togglePulseMetadata,
      pulseMetadataLineColor,
      pulseMetadataLineSize,
      pulseMetadataHeelColor,
      pulseMetadataCharFreqColor,
      pulseMetadataKneeColor,
      pulseMetadataPointSize,
      pulseMetadataShowLabels,
      pulseMetadataDurationFreqLineColor,
      colorsExpanded,
    };
  },
});
</script>

<template>
  <div
    v-if="compressed"
    class="d-flex align-center"
  >
    <v-menu
      v-if="compressed"
      location="top"
      :close-on-content-click="false"
      open-on-hover
    >
      <template #activator="{ props: menuProps }">
        <v-icon
          v-if="!pulseMetadataLoading"
          v-bind="menuProps"
          size="25"
          :color="viewPulseMetadataLayer ? 'blue' : ''"
          @click="togglePulseMetadata()"
        >
          mdi-chart-line-variant
        </v-icon>
        <v-progress-circular
          v-else
          indeterminate
          size="25"
          color="primary"
        />
      </template>
      <v-card min-width="260">
        <v-card-title class="text-subtitle-1 px-3 pt-3">
          Pulse metadata style
        </v-card-title>
        <v-card-text class="pt-0">
          <div class="mt-1 d-flex align-center">
            <span class="text-body-2 mr-2">Show frequency labels</span>
            <v-switch
              v-model="pulseMetadataShowLabels"
              hide-details
              density="compact"
              class="mt-0 pt-0"
            />
          </div>
          <v-expansion-panels
            v-model="colorsExpanded"
            class="mt-2"
          >
            <v-expansion-panel>
              <v-expansion-panel-title>Colors</v-expansion-panel-title>
              <v-expansion-panel-text>
                <div class="d-flex align-center mb-2">
                  <span
                    class="text-body-2 mr-2"
                    style="min-width: 90px"
                  >
                    Line
                  </span>
                  <input
                    v-model="pulseMetadataLineColor"
                    type="color"
                    class="pulse-metadata-color-input mr-2"
                  >
                  <span class="text-caption mr-2">{{ pulseMetadataLineColor }}</span>
                </div>
                <div class="d-flex align-center mb-2">
                  <span
                    class="text-body-2 mr-2"
                    style="min-width: 90px"
                  >
                    Duration/Freq
                  </span>
                  <input
                    v-model="pulseMetadataDurationFreqLineColor"
                    type="color"
                    class="pulse-metadata-color-input mr-2"
                  >
                  <span class="text-caption mr-2">{{ pulseMetadataDurationFreqLineColor }}</span>
                </div>
                <div class="d-flex align-center mb-2">
                  <span
                    class="text-body-2 mr-2"
                    style="min-width: 90px"
                  >
                    Heel
                  </span>
                  <input
                    v-model="pulseMetadataHeelColor"
                    type="color"
                    class="pulse-metadata-color-input mr-2"
                  >
                  <span class="text-caption">{{ pulseMetadataHeelColor }}</span>
                </div>
                <div class="d-flex align-center mb-2">
                  <span
                    class="text-body-2 mr-2"
                    style="min-width: 90px"
                  >
                    Char. freq.
                  </span>
                  <input
                    v-model="pulseMetadataCharFreqColor"
                    type="color"
                    class="pulse-metadata-color-input mr-2"
                  >
                  <span class="text-caption">{{ pulseMetadataCharFreqColor }}</span>
                </div>
                <div class="d-flex align-center mb-2">
                  <span
                    class="text-body-2 mr-2"
                    style="min-width: 90px"
                  >
                    Knee
                  </span>
                  <input
                    v-model="pulseMetadataKneeColor"
                    type="color"
                    class="pulse-metadata-color-input mr-2"
                  >
                  <span class="text-caption">{{ pulseMetadataKneeColor }}</span>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
          <div class="mt-3">
            <span class="text-body-2">Point size</span>
            <v-slider
              v-model="pulseMetadataPointSize"
              min="1"
              max="20"
              step="1"
              hide-details
              density="compact"
              class="mt-1"
            >
              <template #thumb-label="{ modelValue }">
                {{ modelValue }}
              </template>
            </v-slider>
          </div>
          <div class="mt-3">
            <span class="text-body-2">Line size</span>
            <v-slider
              v-model="pulseMetadataLineSize"
              min="1"
              max="20"
              step="1"
              hide-details
              density="compact"
            >
              <template #thumb-label="{ modelValue }">
                {{ modelValue }}
              </template>
            </v-slider>
          </div>
        </v-card-text>
      </v-card>
    </v-menu>
  </div>
</template>

<style scoped>
.pulse-metadata-color-input {
  width: 28px;
  height: 28px;
  padding: 0;
  border: 1px solid rgba(0, 0, 0, 0.2);
  border-radius: 4px;
  cursor: pointer;
}
</style>
