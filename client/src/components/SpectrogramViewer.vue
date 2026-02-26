<script lang="ts">
import { computed, defineComponent, onMounted, onUnmounted, PropType, ref, Ref, watch } from "vue";
import { SpectroInfo, spectroToCenter, useGeoJS } from "./geoJS/geoJSUtils";
import {
  patchAnnotation,
  patchSequenceAnnotation,
  putAnnotation,
  putSequenceAnnotation,
  SpectrogramAnnotation,
  SpectrogramSequenceAnnotation,
} from "../api/api";
import LayerManager from "./geoJS/LayerManager.vue";
import PulseMetadataTooltip from "./PulseMetadataTooltip.vue";
import type { PulseMetadataTooltipData } from "./geoJS/layers/pulseMetadataLayer";
import { GeoEvent } from "geojs";
import geo from "geojs";
import useState from "@use/useState";
import { getImageDimensions } from "@use/useUtils";

export default defineComponent({
  name: "SpectroViewer",
  components: { LayerManager, PulseMetadataTooltip },
  props: {
    images: { type: Array as PropType<HTMLImageElement[]>, default: () => [] },
    maskImages: { type: Array as PropType<HTMLImageElement[]>, default: () => [] },
    spectroInfo: { type: Object as PropType<SpectroInfo>, required: true },
    recordingId: { type: String as PropType<string | null>, required: true },
    compressed: { type: Boolean, required: true }
  },
  emits: ["update:annotation", "create:annotation", "geoViewerRef", "hoverData"],
  setup(props, { emit }) {
    const {
      annotations,
      sequenceAnnotations,
      selectedId,
      selectedType,
      creationType,
      backgroundColor,
      scaledVals,
      configuration,
      scaledWidth,
      scaledHeight,
      contoursEnabled,
      imageOpacity,
      viewMaskOverlay,
      maskOverlayOpacity,
    } = useState();

    const containerRef: Ref<HTMLElement | undefined> = ref();
    const pulseMetadataTooltipData = ref<PulseMetadataTooltipData | null>(null);
    const geoJS = useGeoJS();
    const initialized = ref(false);
    const cursor = ref("");
    const imageCursorRef: Ref<HTMLElement | undefined> = ref();

    const setCursor = (newCursor: string) => { cursor.value = newCursor; };

    function updateScaledDimensions() {
      const { width, height } = getImageDimensions(props.images, props.spectroInfo);
      scaledWidth.value = width * scaledVals.value.x;
      scaledHeight.value = height * scaledVals.value.y;
      if (scaledWidth.value < width) {
        scaledWidth.value = width;
      }
      if (scaledHeight.value < height) {
        scaledHeight.value = height;
      }
    }

    const cursorHandler = {
      handleMouseLeave() {
        if (imageCursorRef.value) {
          imageCursorRef.value.style.display = "none";
        }
      },
      handleMouseEnter() {
        if (imageCursorRef.value) {
          imageCursorRef.value.style.display = "block";
        }
      },
      handleMouseMove(evt: MouseEvent) {
        const offsetX = evt.clientX + 10;
        const offsetY = evt.clientY - 25;
        window.requestAnimationFrame(() => {
          if (imageCursorRef.value) {
            imageCursorRef.value.style.transform = `translate(${offsetX}px, ${offsetY}px)`;
          }
        });
      },
    };

    const mouseMoveEvent = (e: GeoEvent) => {
      if (!props.spectroInfo) return;
      const { x, y } = e.geo;
      const width = Math.max(scaledWidth.value, props.spectroInfo.width);
      const height = Math.max(scaledHeight.value, props.spectroInfo.height);

      const freq = height - y >= 0
        ? ((height - y) * (props.spectroInfo.high_freq - props.spectroInfo.low_freq)) / height / 1000 + props.spectroInfo.low_freq / 1000
        : -1;

      let time = -1;
      if (x >= 0 && height - y >= 0) {
        if (!props.compressed) {
          time = x * ((props.spectroInfo.end_time - props.spectroInfo.start_time) / width);
        } else if (props.spectroInfo.start_times && props.spectroInfo.end_times) {
          const timeLength = props.spectroInfo.end_time - props.spectroInfo.start_time;
          const timeToPixels = (width / timeLength) * scaledVals.value.x;
          let offsetAdditive = 0;
          for (let i = 0; i < props.spectroInfo.start_times.length; i++) {
            const start_time = props.spectroInfo.start_times[i];
            const end_time = props.spectroInfo.end_times[i];
            const startX = offsetAdditive;
            const endX = offsetAdditive + (end_time - start_time) * timeToPixels;
            if (x > startX && x < endX) {
              time = start_time + (x - offsetAdditive) / timeToPixels;
              break;
            }
            offsetAdditive += (end_time - start_time) * timeToPixels;
          }
        }
      }
      emit("hoverData", { time, freq });
    };

    const effectiveImageOpacity = computed(() => (contoursEnabled.value ? imageOpacity.value : 1));

    function initializeViewerAndImages() {
      updateScaledDimensions();
      if (containerRef.value && !geoJS.getGeoViewer().value) {
        geoJS.initializeViewer(containerRef.value, scaledWidth.value, scaledHeight.value, false, props.images.length);
        geoJS.getGeoViewer().value.geoOn(geo.event.mousemove, mouseMoveEvent);
      }
      if (props.images.length) {
        geoJS.drawImages(props.images, scaledWidth.value, scaledHeight.value, true, effectiveImageOpacity.value);
      }
      if (viewMaskOverlay.value && props.maskImages.length) {
        geoJS.drawMaskImages(props.maskImages, scaledWidth.value, scaledHeight.value, maskOverlayOpacity.value);
      }
      initialized.value = true;
      emit("geoViewerRef", geoJS.getGeoViewer());

      if (props.compressed) {
        scaledVals.value = { x: configuration.value.spectrogram_x_stretch, y: 1 };
        updateScaledDimensions();
        if (props.images.length) {
          geoJS.drawImages(props.images, scaledWidth.value, scaledHeight.value, false, effectiveImageOpacity.value);
        }
        if (viewMaskOverlay.value && props.maskImages.length) {
          geoJS.drawMaskImages(props.maskImages, scaledWidth.value, scaledHeight.value, maskOverlayOpacity.value);
        }
      }
    }

    onMounted(() => {
      initialized.value = false;
      scaledHeight.value = 0;
      scaledWidth.value = 0;
      scaledVals.value = { x: 1, y: 1 };
    });

    watch([containerRef, () => props.spectroInfo, () => props.images], initializeViewerAndImages);

    watch(() => props.spectroInfo, () => {
      updateScaledDimensions();
      geoJS.resetMapDimensions(scaledWidth.value, scaledHeight.value);
      geoJS.getGeoViewer().value.bounds({
        left: 0,
        top: 0,
        bottom: scaledHeight.value,
        right: scaledWidth.value,
      });
      if (props.images.length) {
        geoJS.drawImages(props.images, scaledWidth.value, scaledHeight.value, true, effectiveImageOpacity.value);
      }
      if (viewMaskOverlay.value && props.maskImages.length) {
        geoJS.drawMaskImages(props.maskImages, scaledWidth.value, scaledHeight.value, maskOverlayOpacity.value);
      }
    });

    const updateAnnotation = async (
      annotation: SpectrogramAnnotation | SpectrogramSequenceAnnotation
    ) => {
      if (props.recordingId !== null && selectedId.value !== null) {
        if (selectedType.value === "pulse") {
          await patchAnnotation(props.recordingId, selectedId.value, annotation);
        } else if (selectedType.value === "sequence") {
          await patchSequenceAnnotation(props.recordingId, selectedId.value, annotation);
        }
        emit("update:annotation", annotation);
      }
    };

    const createAnnotation = async (
      annotation: SpectrogramAnnotation | SpectrogramSequenceAnnotation
    ) => {
      if (props.recordingId !== null) {
        if (creationType.value === "pulse") {
          const response = await putAnnotation(props.recordingId, annotation);
          emit("create:annotation", response.data.id);
        } else if (creationType.value === "sequence") {
          const response = await putSequenceAnnotation(props.recordingId, annotation);
          emit("create:annotation", response.data.id);
        }
      }
    };

    let skipNextSelected = false;
    watch(selectedId, () => {
      if (skipNextSelected) {
        skipNextSelected = false;
        return;
      }
      const found =
        selectedType.value === "pulse"
          ? annotations.value.find((item) => item.id === selectedId.value)
          : sequenceAnnotations.value.find((item) => item.id === selectedId.value);
      if (found && props.spectroInfo) {
        const [x, y] = spectroToCenter(found, props.spectroInfo, selectedType.value);
        const bounds = geoJS.getGeoViewer().value.bounds();
        if (x < bounds.left || x > bounds.right) {
          geoJS.getGeoViewer().value.center({ x, y });
        }
      }
    });

    const wheelEvent = (event: WheelEvent) => {
      const incrementX = 0.1, incrementY = 0.1;

      if (event.ctrlKey) {
        scaledVals.value.x += event.deltaY > 0 ? -incrementX : incrementX;
        if (scaledVals.value.x < 1) scaledVals.value.x = 1;
        updateScaledDimensions();
        if (props.images.length) {
          geoJS.drawImages(props.images, scaledWidth.value, scaledHeight.value, false, effectiveImageOpacity.value);
        }
        if (viewMaskOverlay.value && props.maskImages.length) {
          geoJS.drawMaskImages(props.maskImages, scaledWidth.value, scaledHeight.value, maskOverlayOpacity.value);
        }
      } else if (event.shiftKey) {
        scaledVals.value.y += event.deltaY > 0 ? -incrementY : incrementY;
        if (scaledVals.value.y < 1) scaledVals.value.y = 1;
        updateScaledDimensions();
        if (props.images.length) {
          geoJS.drawImages(props.images, scaledWidth.value, scaledHeight.value, false, effectiveImageOpacity.value);
        }
        if (viewMaskOverlay.value && props.maskImages.length) {
          geoJS.drawMaskImages(props.maskImages, scaledWidth.value, scaledHeight.value, maskOverlayOpacity.value);
        }
      }
    };

    onUnmounted(() => geoJS.destroyGeoViewer());

    watch([contoursEnabled, imageOpacity], () => {
      if (props.images.length) {
        geoJS.drawImages(props.images, scaledWidth.value, scaledHeight.value, false, effectiveImageOpacity.value);
      }
    });

    watch([viewMaskOverlay, maskOverlayOpacity, () => props.maskImages], () => {
      if (viewMaskOverlay.value && props.maskImages.length) {
        geoJS.drawMaskImages(props.maskImages, scaledWidth.value, scaledHeight.value, maskOverlayOpacity.value);
      } else {
        geoJS.clearMaskQuadFeatures(true);
      }
    });

    function onPulseMetadataTooltip(data: PulseMetadataTooltipData | null) {
      pulseMetadataTooltipData.value = data;
    }

    return {
      containerRef,
      pulseMetadataTooltipData,
      onPulseMetadataTooltip,
      geoViewerRef: geoJS.getGeoViewer(),
      initialized,
      cursor,
      setCursor,
      updateAnnotation,
      createAnnotation,
      cursorHandler,
      imageCursorRef,
      wheelEvent,
      scaledWidth,
      scaledHeight,
      backgroundColor
    };
  },
});
</script>

<template>
  <div
    class="video-annotator"
    :style="{ backgroundColor: backgroundColor }"
    @wheel="wheelEvent($event)"
  >
    <div
      id="spectro"
      ref="containerRef"
      class="playback-container"
      :style="{ cursor: cursor }"
      @mousemove="cursorHandler.handleMouseMove"
      @mouseleave="cursorHandler.handleMouseLeave"
      @mouseover="cursorHandler.handleMouseEnter"
    >
      <PulseMetadataTooltip :data="pulseMetadataTooltipData" />
    </div>
    <layer-manager
      v-if="initialized"
      :geo-viewer-ref="geoViewerRef"
      :spectro-info="spectroInfo"
      :scaled-width="scaledWidth"
      :scaled-height="scaledHeight"
      :recording-id="recordingId"
      @update:annotation="updateAnnotation($event)"
      @create:annotation="createAnnotation($event)"
      @set-cursor="setCursor($event)"
      @pulse-metadata-tooltip="onPulseMetadataTooltip($event)"
    />
    <div
      ref="imageCursorRef"
      class="imageCursor"
    >
      <v-icon color="white">
        {{ cursor }}
      </v-icon>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.video-annotator {
  position: relative;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  z-index: 0;

  display: flex;
  flex-direction: column;

  .geojs-map {
    margin: 2px;

    &.geojs-map:focus {
      outline: none;
    }
  }

  .playback-container {
    flex: 1;
    position: relative;
  }

  .loadingSpinnerContainer {
    z-index: 20;
    margin: 0;
    position: absolute;
    top: 50%;
    left: 50%;
    -ms-transform: translate(-50%, -50%);
    transform: translate(-50%, -50%);
  }

  .geojs-map.annotation-input {
    cursor: inherit;
  }
}

.black-background {
  background-color: black;
}

.white-background {
  background-color: white;
}

.imageCursor {
  z-index: 9999; //So it will be above the annotator layers
  position: fixed;
  backface-visibility: hidden;
  top: 0;
  left: 0;
  pointer-events: none;
}
</style>
