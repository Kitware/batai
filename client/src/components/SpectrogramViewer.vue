<script lang="ts">
import { defineComponent, PropType, ref, Ref, watch } from "vue";
import { SpectroInfo, useGeoJS } from './geoJS/geoJSUtils';
import { patchAnnotation, putAnnotation, SpectrogramAnnotation } from "../api/api";
import LayerManager from "./geoJS/LayerManager.vue";

export default defineComponent({
  name: "SpectroViewer",
  components: {
    LayerManager
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
    annotations: {
      type: Array as PropType<SpectrogramAnnotation[]>,
      default: () => [],
    },
    selectedId: {
        type: Number as PropType<number | null>,
        default: null,
    },
    recordingId: {
      type: String as PropType<string | null>,
      required: true,
    },
    grid: {
      type: Boolean,
      default: true,
    }
  },
  emits: ['update:annotation', 'create:annotation', 'selected', 'geoViewerRef'],
  setup(props, { emit }) {
    const containerRef: Ref<HTMLElement | undefined> = ref();
    const geoJS = useGeoJS();
    const initialized  = ref(false);

    watch(containerRef, () => {
      const { naturalWidth, naturalHeight } = props.image;
      if (containerRef.value)
      geoJS.initializeViewer(containerRef.value, naturalWidth, naturalHeight);
      geoJS.drawImage(props.image, naturalWidth, naturalHeight);
      initialized.value = true;
      emit('geoViewerRef', geoJS.getGeoViewer());
    });

    const updateAnnotation = async (annotation: SpectrogramAnnotation) => {
      // We call the patch on the selected annotation
      if (props.recordingId !== null && props.selectedId !== null) {
        await patchAnnotation(props.recordingId, props.selectedId, annotation);
        emit('update:annotation', annotation);
      }
    };

    const createAnnotation = async (annotation: SpectrogramAnnotation) => {
      // We call the patch on the selected annotation
      if (props.recordingId !== null) {
        const response =  await putAnnotation(props.recordingId, annotation);
        emit('create:annotation', response.data.id);
      }
    };



    return {
      containerRef,
      geoViewerRef: geoJS.getGeoViewer(),
      initialized,
      updateAnnotation,
      createAnnotation,
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
    />
    <layer-manager
      v-if="initialized"
      :geo-viewer-ref="geoViewerRef"
      :spectro-info="spectroInfo"
      :annotations="annotations"
      :selected-id="selectedId"
      :grid="grid"
      @selected="$emit('selected',$event)"
      @update:annotation="updateAnnotation($event)"
      @create:annotation="createAnnotation($event)"
    />
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
    margin:2px;
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
}</style>
