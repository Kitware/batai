<script lang="ts">
import { defineComponent, nextTick, PropType, ref, watch } from "vue";
import type { PulseMetadataTooltipData } from "./geoJS/layers/pulseMetadataLayer";

const MIN_WIDTH = 180;

export default defineComponent({
  name: "PulseMetadataTooltip",
  props: {
    data: {
      type: Object as PropType<PulseMetadataTooltipData | null>,
      default: null,
    },
  },
  setup(props) {
    const cardRef = ref<HTMLElement | null>(null);
    const clampedLeft = ref(0);

    function updateClampedLeft() {
      const d = props.data;
      if (!d) return;
      nextTick(() => {
        nextTick(() => {
          const card = cardRef.value;
          const containerWidth = card?.parentElement?.clientWidth ?? 9999;
          const tooltipWidth = card?.offsetWidth || MIN_WIDTH;
          clampedLeft.value = Math.max(
            0,
            Math.min(d.bbox.left, containerWidth - tooltipWidth),
          );
        });
      });
    }

    watch(
      () => props.data,
      (newData) => {
        if (!newData) return;
        updateClampedLeft();
      },
      { immediate: true },
    );

    return { cardRef, clampedLeft };
  },
});
</script>

<template>
  <transition name="fade">
    <v-card
      v-if="data"
      ref="cardRef"
      class="pulse-metadata-tooltip"
      :style="{
        position: 'absolute',
        left: `${clampedLeft}px`,
        top: '0',
        zIndex: 9998,
        minWidth: '180px',
      }"
      density="compact"
      variant="elevated"
      elevation="4"
    >
      <v-card-text class="pa-2 text-body-2">
        <div class="d-flex flex-column gap-1">
          <div
            v-if="data.kneeKhz != null"
            class="d-flex align-center"
          >
            <span
              v-if="data.kneeColor"
              class="color-swatch"
              :style="{ backgroundColor: data.kneeColor }"
            />
            <span class="text-caption text-medium-emphasis mr-2">Knee</span>
            <span>{{ data.kneeKhz.toFixed(1) }} kHz</span>
          </div>
          <div v-if="data.slopeAtHiFcKneeKhzPerMs != null"> 
            <span
              class="text-caption ml-4 text-medium-emphasis"
            >
              ({{ data.slopeAtHiFcKneeKhzPerMs.toFixed(2) }} kHz/ms)
            </span>
          </div>
          <div
            v-if="data.fcKhz != null"
            class="d-flex align-center"
          >
            <span
              v-if="data.charFreqColor"
              class="color-swatch"
              :style="{ backgroundColor: data.charFreqColor }"
            />
            <span class="text-caption text-medium-emphasis mr-2">Fc</span>
            <span>{{ data.fcKhz.toFixed(1) }} kHz</span>
          </div>
          <div v-if="data.slopeAtFcKhzPerMs != null"> 
            <span
              class="text-caption ml-4 text-medium-emphasis"
            >
              ({{ data.slopeAtFcKhzPerMs.toFixed(2) }} kHz/ms)
            </span>
          </div>
          <div
            v-if="data.heelKhz != null"
            class="d-flex align-center"
          >
            <span
              v-if="data.heelColor"
              class="color-swatch"
              :style="{ backgroundColor: data.heelColor }"
            />
            <span class="text-caption text-medium-emphasis mr-2">Heel</span>
            <span>{{ data.heelKhz.toFixed(1) }} kHz</span>
          </div>
          <div v-if="data.slopeAtLowFcHeelKhzPerMs != null"> 
            <span
              class="text-caption ml-4 text-medium-emphasis"
            >
              ({{ data.slopeAtLowFcHeelKhzPerMs.toFixed(2) }} kHz/ms)
            </span>
          </div>
          <div class="d-flex align-center">
            <span class="text-caption text-medium-emphasis mr-2">Duration</span>
            <span>{{ data.durationMs.toFixed(1) }} ms</span>
          </div>
          <div class="d-flex align-center">
            <span class="text-caption text-medium-emphasis mr-2">Fₘᵢₙ</span>
            <span>{{ data.fminKhz.toFixed(1) }} kHz</span>
          </div>
          <div class="d-flex align-center">
            <span class="text-caption text-medium-emphasis mr-2">Fₘₐₓ</span>
            <span>{{ data.fmaxKhz.toFixed(1) }} kHz</span>
          </div>
        </div>
      </v-card-text>
    </v-card>
  </transition>
</template>

<style scoped>
.pulse-metadata-tooltip {
  pointer-events: none;
}

.color-swatch {
  width: 12px;
  height: 12px;
  border-radius: 2px;
  border: 1px solid rgba(0, 0, 0, 0.2);
  flex-shrink: 0;
  margin-right: 4px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.1s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
