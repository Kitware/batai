<!-- eslint-disable @typescript-eslint/no-explicit-any -->
<script lang="ts">
import { defineComponent, nextTick, PropType, ref, Ref, watch } from "vue";
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
    const yScale = ref(1);
    const polyLayerCreated = ref(false);
    let downState: any;

    const {
      scaledWidth,
      scaledHeight,
      blackBackground,
    } = useState();

    function updateViewerAndImages() {
      const { width, height } = getImageDimensions(props.images);
      if (containerRef.value) {
        clientHeight.value = containerRef.value.clientHeight;
      }

      if (containerRef.value && !geoJS.getGeoViewer().value) {
        geoJS.initializeViewer(containerRef.value, width, height, true);
      }
      geoJS.resetMapDimensions(width, height);
      geoJS.getGeoViewer().value.bounds({ left: 0, top: 0, bottom: height, right: width });

      // Calculate yScale
      const camera = geoJS.getGeoViewer().value.camera();
      const coords = camera.worldToDisplay({ x: 0, y: 0 });
      const end = camera.worldToDisplay({ x: 0, y: height });
      const diff = coords.y - end.y;
      yScale.value = diff ? (clientHeight.value * 0.5) / diff : 1;

      if (props.images.length) {
        geoJS.drawImages(props.images, scaledWidth.value, scaledHeight.value, false);
      }
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

    return {
      containerRef,
      geoViewerRef: geoJS.getGeoViewer(),
      initialized,
      yScale,
      scaledWidth,
      scaledHeight,
      blackBackground,
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
      :class="{ 'black-background': blackBackground, 'white-background': !blackBackground }"
    />
    <layer-manager
      v-if="initialized"
      :geo-viewer-ref="geoViewerRef"
      :spectro-info="spectroInfo"
      :y-scale="yScale"
      :scaled-width="scaledWidth"
      :scaled-height="scaledHeight"
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
