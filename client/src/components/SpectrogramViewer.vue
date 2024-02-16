<script lang="ts">
import { defineComponent, PropType, ref, Ref, watch } from "vue";
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
import useState from "../use/useState";

export default defineComponent({
  name: "SpectroViewer",
  components: {
    LayerManager,
  },
  props: {
    image: {
      type: Object as PropType<HTMLImageElement>,
      required: true,
    },
    spectroInfo: {
      type: Object as PropType<SpectroInfo | undefined>,
      default: () => undefined,
    },
    recordingId: {
      type: String as PropType<string | null>,
      required: true,
    },
  },
  emits: [
    "update:annotation",
    "create:annotation",
    "geoViewerRef",
    "hoverData",
  ],
  setup(props, { emit }) {
    const { annotations, selectedId, selectedType, creationType } = useState();
    const containerRef: Ref<HTMLElement | undefined> = ref();
    const geoJS = useGeoJS();
    const initialized = ref(false);
    const cursor = ref("");
    const imageCursorRef: Ref<HTMLElement | undefined> = ref();
    const setCursor = (newCursor: string) => {
      cursor.value = newCursor;
    };

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
      const { x, y } = e.geo;
      if (!props.spectroInfo) {
        return;
      }
      const freq =
        props.spectroInfo.height - y >= 0
          ? ((props.spectroInfo.height - y) *
              (props.spectroInfo.high_freq - props.spectroInfo.low_freq)) /
              props.spectroInfo.height /
              1000 +
            props.spectroInfo.low_freq / 1000
          : -1;

      if (!props.spectroInfo.end_times && !props.spectroInfo.start_times) {
        if (x >= 0 && props.spectroInfo.height - y >= 0) {
          const time =
            x *
            ((props.spectroInfo.end_time - props.spectroInfo.start_time) / props.spectroInfo.width);
          emit("hoverData", { time, freq });
        } else {
          emit("hoverData", { time: -1, freq: -1 });
        }
      } else if (
        props.spectroInfo &&
        props.spectroInfo.start_times &&
        props.spectroInfo.end_times
      ) {
        // compressed view
        if (x >= 0 && props.spectroInfo.height - y >= 0) {
          const timeLength = props.spectroInfo.end_time - props.spectroInfo.start_time;
          const timeToPixels = props.spectroInfo.width / timeLength;
          // find X in the range
          let offsetAdditive = 0;
          for (let i = 0; i < props.spectroInfo.start_times.length; i += 1) {
            const start_time = props.spectroInfo.start_times[i];
            const end_time = props.spectroInfo.end_times[i];
            const startX = offsetAdditive;
            const endX = offsetAdditive + (end_time - start_time) * timeToPixels;

            if (x > startX && x < endX) {
              const timeOffset = x - offsetAdditive;
              const time = start_time + timeOffset / timeToPixels;
              emit("hoverData", { time, freq });
              return;
            }
            offsetAdditive += (end_time - start_time) * timeToPixels;
          }
        } else {
          emit("hoverData", { time: -1, freq: -1 });
        }
      }
    };
    watch(containerRef, () => {
      const { naturalWidth, naturalHeight } = props.image;
      if (containerRef.value)
        geoJS.initializeViewer(containerRef.value, naturalWidth, naturalHeight);
      geoJS.drawImage(props.image, naturalWidth, naturalHeight);
      initialized.value = true;
      emit("geoViewerRef", geoJS.getGeoViewer());
      geoJS.getGeoViewer().value.geoOn(geo.event.mousemove, mouseMoveEvent);
    });

    const updateAnnotation = async (annotation: SpectrogramAnnotation | SpectrogramTemporalAnnotation) => {
      // We call the patch on the selected annotation
      if (props.recordingId !== null && selectedId.value !== null) {
        if (selectedType.value === 'pulse') {
          await patchAnnotation(props.recordingId, selectedId.value, annotation);
        } else if (selectedType.value === 'sequence') {
          await patchTemporalAnnotation(props.recordingId, selectedId.value, annotation);
        }
        emit("update:annotation", annotation);
      }
    };

    const createAnnotation = async (annotation: SpectrogramAnnotation | SpectrogramTemporalAnnotation) => {
      // We call the patch on the selected annotation
      if (props.recordingId !== null) {
        if (creationType.value === 'pulse') {
          const response = await putAnnotation(props.recordingId, annotation);
          emit("create:annotation", response.data.id);
        } else if (creationType.value === 'sequence') {
          const response = await putTemporalAnnotation(props.recordingId, annotation);
          emit("create:annotation", response.data.id);
        }
      }
    };
    let skipNextSelected = false;
    watch(
      selectedId,
      () => {
        if (skipNextSelected) {
          skipNextSelected = false;
          return;
        }
        const found = annotations.value.find((item) => item.id === selectedId.value);
        if (found && props.spectroInfo) {
          const center = spectroToCenter(found, props.spectroInfo);
          const x = center[0];
          const y = center[1];
          const bounds = geoJS.getGeoViewer().value.bounds();
          if (x < bounds.left || x > bounds.right) {
            geoJS.getGeoViewer().value.center({ x, y });
          }
        }
      }
    );


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
    };
  },
});
</script>

<template>
  <div class="video-annotator">
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
  height: 60vh;
  background-color: black;

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
.imageCursor {
  z-index: 9999; //So it will be above the annotator layers
  position: fixed;
  backface-visibility: hidden;
  top: 0;
  left: 0;
  pointer-events: none;
}
</style>
