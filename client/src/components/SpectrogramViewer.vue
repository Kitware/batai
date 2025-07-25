<script lang="ts">
import { defineComponent, onMounted, onUnmounted, PropType, ref, Ref, watch } from "vue";
import { SpectroInfo, spectroToCenter, useGeoJS } from "./geoJS/geoJSUtils";
import {
  patchAnnotation,
  patchTemporalAnnotation,
  putAnnotation,
  putTemporalAnnotation,
  SpectrogramAnnotation,
  SpectrogramTemporalAnnotation,
} from "../api/api";
import LayerManager from "./geoJS/LayerManager.vue";
import { GeoEvent } from "geojs";
import geo from "geojs";
import useState from "@use/useState";
import { getImageDimensions } from "@use/useUtils";

export default defineComponent({
  name: "SpectroViewer",
  components: { LayerManager },
  props: {
    images: { type: Array as PropType<HTMLImageElement[]>, default: () => [] },
    spectroInfo: { type: Object as PropType<SpectroInfo>, required: true },
    recordingId: { type: String as PropType<string | null>, required: true },
    compressed: { type: Boolean, required: true }
  },
  emits: ["update:annotation", "create:annotation", "geoViewerRef", "hoverData"],
  setup(props, { emit }) {
    const {
      annotations,
      temporalAnnotations,
      selectedId,
      selectedType,
      creationType,
      blackBackground,
      scaledVals,
      configuration,
    } = useState();

    const containerRef: Ref<HTMLElement | undefined> = ref();
    const geoJS = useGeoJS();
    const initialized = ref(false);
    const cursor = ref("");
    const scaledWidth = ref(0);
    const scaledHeight = ref(0);
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

    function initializeViewerAndImages() {
      updateScaledDimensions();
      if (containerRef.value && !geoJS.getGeoViewer().value) {
        geoJS.initializeViewer(containerRef.value, scaledWidth.value, scaledHeight.value, false, props.images.length);
        geoJS.getGeoViewer().value.geoOn(geo.event.mousemove, mouseMoveEvent);
      }
      if (props.images.length) {
        geoJS.drawImages(props.images, scaledWidth.value, scaledHeight.value);
      }
      initialized.value = true;
      emit("geoViewerRef", geoJS.getGeoViewer());

      if (props.compressed) {
        scaledVals.value = { x: configuration.value.spectrogram_x_stretch, y: 1 };
        updateScaledDimensions();
        if (props.images.length) {
          geoJS.drawImages(props.images, scaledWidth.value, scaledHeight.value, false);
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
        geoJS.drawImages(props.images, scaledWidth.value, scaledHeight.value);
      }
    });

    const updateAnnotation = async (
      annotation: SpectrogramAnnotation | SpectrogramTemporalAnnotation
    ) => {
      if (props.recordingId !== null && selectedId.value !== null) {
        if (selectedType.value === "pulse") {
          await patchAnnotation(props.recordingId, selectedId.value, annotation);
        } else if (selectedType.value === "sequence") {
          await patchTemporalAnnotation(props.recordingId, selectedId.value, annotation);
        }
        emit("update:annotation", annotation);
      }
    };

    const createAnnotation = async (
      annotation: SpectrogramAnnotation | SpectrogramTemporalAnnotation
    ) => {
      if (props.recordingId !== null) {
        if (creationType.value === "pulse") {
          const response = await putAnnotation(props.recordingId, annotation);
          emit("create:annotation", response.data.id);
        } else if (creationType.value === "sequence") {
          const response = await putTemporalAnnotation(props.recordingId, annotation);
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
          : temporalAnnotations.value.find((item) => item.id === selectedId.value);
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
          geoJS.drawImages(props.images, scaledWidth.value, scaledHeight.value, false);
        }
      } else if (event.shiftKey) {
        scaledVals.value.y += event.deltaY > 0 ? -incrementY : incrementY;
        if (scaledVals.value.y < 1) scaledVals.value.y = 1;
        updateScaledDimensions();
        if (props.images.length) {
          geoJS.drawImages(props.images, scaledWidth.value, scaledHeight.value, false);
        }
      }
    };

    onUnmounted(() => geoJS.destroyGeoViewer());

    return {
      containerRef,
      geoViewerRef: geoJS.getGeoViewer(),
      initialized,
      cursor,
      setCursor,
      updateAnnotation,
      createAnnotation,
      cursorHandler,
      imageCursorRef,
      blackBackground,
      wheelEvent,
      scaledWidth,
      scaledHeight,
    };
  },
});
</script>

<template>
  <div
    class="video-annotator"
    :class="{ 'black-background': blackBackground, 'white-background': !blackBackground }"
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
    />
    <layer-manager
      v-if="initialized"
      :geo-viewer-ref="geoViewerRef"
      :spectro-info="spectroInfo"
      :scaled-width="scaledWidth"
      :scaled-height="scaledHeight"
      @update:annotation="updateAnnotation($event)"
      @create:annotation="createAnnotation($event)"
      @set-cursor="setCursor($event)"
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
