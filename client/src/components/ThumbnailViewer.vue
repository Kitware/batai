<!-- eslint-disable @typescript-eslint/no-explicit-any -->
<script lang="ts">
import { computed, defineComponent, nextTick, PropType, ref, Ref, watch } from "vue";
import { SpectroInfo, useGeoJS } from './geoJS/geoJSUtils';
import { OtherUserAnnotations, SpectrogramAnnotation } from "../api/api";
import LayerManager from "./geoJS/LayerManager.vue";
import geo, { GeoEvent } from "geojs";
import { getImageDimensions } from "@use/useUtils";
import useState from "@use/useState";


export default defineComponent({
  name: "ThumbnailViewer",
  components: { LayerManager },
  props: {
    images: { type: Array as PropType<HTMLImageElement[]>, default: () => [] },
    maskImages: { type: Array as PropType<HTMLImageElement[]>, default: () => [] },
    waveplotImages: { type: Array as PropType<HTMLImageElement[]>, default: () => [] },
    spectroInfo: { type: Object as PropType<SpectroInfo | undefined>, default: () => undefined },
    annotations: { type: Array as PropType<SpectrogramAnnotation[]>, default: () => [] },
    otherUserAnnotations: { type: Object as PropType<OtherUserAnnotations>, default: () => ({}) },
    selectedId: { type: Number as PropType<number | null>, default: null },
    recordingId: { type: String as PropType<string | null>, required: true },
    parentGeoViewerRef: { type: Object as PropType<any>, required: true }
  },
  emits: ['selected'],
  setup(props) {
    const containerRef: Ref<HTMLElement | undefined> = ref();
    const geoJS = useGeoJS();
    const initialized = ref(false);
    const clientHeight = ref(0);
    const polyLayerCreated = ref(false);
    let downState: any;

    const {
      scaledWidth,
      scaledHeight,
      backgroundColor,
      viewMaskOverlay,
      maskOverlayOpacity,
      viewWaveplot,
    } = useState();

    const baseDimensions = computed(() => getImageDimensions(props.images, props.spectroInfo ?? { width: 0, height: 0 }));
    const waveplotDisplayHeight = computed(() => {
      if (!props.waveplotImages.length) return Math.floor(baseDimensions.value.height / 5);
      const totalWaveplotWidth = props.waveplotImages.reduce((sum, img) => sum + img.naturalWidth, 0);
      const waveplotHeight = props.waveplotImages[0]?.naturalHeight ?? 0;
      if (!totalWaveplotWidth || !waveplotHeight) return Math.floor(baseDimensions.value.height / 5);
      const aspectHeight = baseDimensions.value.width * (waveplotHeight / totalWaveplotWidth);
      const capped = Math.min(aspectHeight, baseDimensions.value.height / 3);
      return Math.max(Math.floor(capped), 1);
    });
    const showWaveplot = computed(() =>(viewWaveplot.value && props.waveplotImages.length && waveplotDisplayHeight.value > 0));

    function drawWaveplotIfEnabled(finalW: number, spectroHeight: number) {
      if (showWaveplot.value) {
        geoJS.drawWaveplotImages(
          props.waveplotImages,
          finalW,
          waveplotDisplayHeight.value,
          spectroHeight,
          1
        );
      } else {
        geoJS.clearWaveplotQuadFeatures(true);
      }
    }

    function updateViewerAndImages() {
      const { width, height } = getImageDimensions(props.images);
      if (containerRef.value) {
        clientHeight.value = containerRef.value.clientHeight;
      }

      const finalWidth = scaledWidth.value || width;
      const finalHeight = scaledHeight.value || height;
      const totalHeight = finalHeight + (showWaveplot.value ? waveplotDisplayHeight.value : 0);

      if (containerRef.value && !geoJS.getGeoViewer().value) {
        geoJS.initializeViewer(containerRef.value, finalWidth, totalHeight, true, props.images.length);
      }
      geoJS.resetMapDimensions(finalWidth, totalHeight, 0.3, true);

      if (props.images.length) {
        geoJS.drawImages(props.images, finalWidth, finalHeight);
      }
      if (viewMaskOverlay.value && props.maskImages.length) {
        geoJS.drawMaskImages(props.maskImages, finalWidth, finalHeight, maskOverlayOpacity.value);
      } else {
        geoJS.clearMaskQuadFeatures(true);
      }
      drawWaveplotIfEnabled(finalWidth, finalHeight);
      initialized.value = true;
      nextTick(() => createPolyLayer());
    }

    const createPolyLayer = () => {
      if (polyLayerCreated.value) return;
      const geoViewer = geoJS.getGeoViewer();
      const featureLayer = geoViewer.value.createLayer('feature', { features: ['polygon'] });
      const outlineFeature = featureLayer.createFeature('polygon', {});
      const outlineStyle = {
        stroke: true,
        strokeColor: 'yellow',
        strokeWidth: 1,
        fill: false,
      };
      featureLayer.geoOff();

      featureLayer.geoOn(geo.event.mouseclick, (evt: GeoEvent) => {
        props.parentGeoViewerRef.value.center(evt.geo);
      });
      featureLayer.geoOn(geo.event.actiondown, (evt: GeoEvent) => {
        downState = {
          state: evt.state,
          mouse: evt.mouse,
          center: props.parentGeoViewerRef.value.center(),
          zoom: props.parentGeoViewerRef.value.zoom(),
          rotate: props.parentGeoViewerRef.value.rotation(),
          distanceToOutline: geo.util.distanceToPolygon2d(evt.mouse.geo, outlineFeature.data()[0]) /
            props.parentGeoViewerRef.value.unitsPerPixel(props.parentGeoViewerRef.value.zoom())
        };
      });
      featureLayer.geoOn(geo.event.actionmove, (evt: GeoEvent) => {
        if (evt.state.action === 'overview_pan' && downState) {
          const delta = {
            x: evt.mouse.geo.x - downState.mouse.geo.x,
            y: evt.mouse.geo.y - downState.mouse.geo.y
          };
          const center = props.parentGeoViewerRef.value.center();
          delta.x -= center.x - downState.center.x;
          delta.y -= center.y - downState.center.y;
          if (delta.x || delta.y) {
            props.parentGeoViewerRef.value.center({
              x: center.x + delta.x,
              y: center.y + delta.y
            });
          }
        }
      });

      const onParentPan = () => {
        const parent = props.parentGeoViewerRef.value;
        if (parent.rotation() !== props.parentGeoViewerRef.value.rotation()) {
          props.parentGeoViewerRef.value.rotation(parent.rotation());
          props.parentGeoViewerRef.value.zoom(props.parentGeoViewerRef.value.zoom());
        }
        const size = parent.size();
        outlineFeature.style(outlineStyle);
        const polygon = [[
          parent.displayToGcs({ x: 0, y: 0 }),
          parent.displayToGcs({ x: size.width, y: 0 }),
          parent.displayToGcs({ x: size.width, y: size.height }),
          parent.displayToGcs({ x: 0, y: size.height })
        ]];
        outlineFeature.data(polygon).draw();
      };

      onParentPan();
      props.parentGeoViewerRef.value.geoOff(geo.event.pan, onParentPan);
      props.parentGeoViewerRef.value.geoOn(geo.event.pan, onParentPan);
      polyLayerCreated.value = true;
    };

    watch([() => props.spectroInfo, containerRef], updateViewerAndImages);

    watch([scaledHeight, scaledWidth], () => {
      const { width, height } = getImageDimensions(props.images);
      const finalWidth = scaledWidth.value || width;
      const finalHeight = scaledHeight.value || height;
      const totalHeight = finalHeight + (showWaveplot.value ? waveplotDisplayHeight.value : 0);
      geoJS.resetMapDimensions(finalWidth, totalHeight, 0.3, true);
      geoJS.getGeoViewer().value?.bounds({ left: 0, top: 0, bottom: totalHeight, right: finalWidth });
      if (props.images.length) {
        geoJS.drawImages(props.images, finalWidth, finalHeight);
      }
      if (viewMaskOverlay.value && props.maskImages.length) {
        geoJS.drawMaskImages(props.maskImages, finalWidth, finalHeight, maskOverlayOpacity.value);
      } else {
        geoJS.clearMaskQuadFeatures(true);
      }
      drawWaveplotIfEnabled(finalWidth, finalHeight);
    });

    watch([viewMaskOverlay, maskOverlayOpacity, () => props.maskImages], () => {
      const { width, height } = getImageDimensions(props.images);
      const finalWidth = scaledWidth.value || width;
      const finalHeight = scaledHeight.value || height;
      if (viewMaskOverlay.value && props.maskImages.length) {
        geoJS.drawMaskImages(props.maskImages, finalWidth, finalHeight, maskOverlayOpacity.value);
      } else {
        geoJS.clearMaskQuadFeatures(true);
      }
    });

    watch(viewWaveplot, () => {
      const { width, height } = getImageDimensions(props.images);
      const finalWidth = scaledWidth.value || width;
      const finalHeight = scaledHeight.value || height;
      if (viewWaveplot.value) {
        geoJS.drawWaveplotImages(props.waveplotImages, finalWidth, waveplotDisplayHeight.value, finalHeight, 1);
      } else {
        geoJS.clearWaveplotQuadFeatures(true);
      }
    });

    return {
      containerRef,
      geoViewerRef: geoJS.getGeoViewer(),
      initialized,
      scaledWidth,
      scaledHeight,
      backgroundColor,
    };
  },
});
</script>

<template>
  <div class="video-annotator">
    <div
      id="spectro"
      ref="containerRef"
      :style="{ backgroundColor: backgroundColor }"
      class="playback-container"
    />
    <layer-manager
      v-if="initialized"
      :geo-viewer-ref="geoViewerRef"
      :spectro-info="spectroInfo"
      :scaled-width="scaledWidth"
      :scaled-height="scaledHeight"
      :recording-id="recordingId"
      thumbnail
      @selected="$emit('selected',$event)"
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
  height: 20vh;
  background-color: black;
  border: 2px solid white;

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
