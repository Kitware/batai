<!-- eslint-disable @typescript-eslint/no-explicit-any -->
<script lang="ts">
import { defineComponent, nextTick, PropType, ref, Ref, watch } from "vue";
import { SpectroInfo, useGeoJS } from './geoJS/geoJSUtils';
import { OtherUserAnnotations, SpectrogramAnnotation } from "../api/api";
import LayerManager from "./geoJS/LayerManager.vue";
import geo, { GeoEvent } from "geojs";

export default defineComponent({
  name: "ThumbnailViewer",
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
    otherUserAnnotations: {
      type: Object as PropType<OtherUserAnnotations>,
      default: () => ({}),
    },
    selectedId: {
        type: Number as PropType<number | null>,
        default: null,
    },
    recordingId: {
      type: String as PropType<string | null>,
      required: true,
    },
    parentGeoViewerRef: {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      type: Object as PropType<any>,
      required: true,
    }
  },
  emits: ['selected'],
  setup(props) {
    const containerRef: Ref<HTMLElement | undefined> = ref();
    const geoJS = useGeoJS();
    const initialized  = ref(false);
    const polyLayerCreated= ref(false);
    let downState: {
      state: any,
      mouse: any,
      center: any,
      rotate: any,
      zoom:any,
      distanceToOutline: any,
    };

    const createPolyLayer = () => {
      const geoViewer = geoJS.getGeoViewer();
      const featureLayer = geoViewer.value.createLayer('feature', {feattures: ['polygon']});
      const outlineFeature = featureLayer.createFeature('polygon', {});
      const outlineStyle = {
          stroke: true,
          strokeColor: 'yellow',
          strokeWidth: 1,
          fill: false,
      };
      featureLayer.geoOn(geo.event.mouseclick, (evt: GeoEvent) => {
            props.parentGeoViewerRef.value.center(evt.geo);
      });
      featureLayer.geoOn(geo.event.actiondown, (evt: GeoEvent) => {
            downState = {
                state: evt.state,
                mouse: evt.mouse,
                center:  props.parentGeoViewerRef.value.center(),
                zoom:  props.parentGeoViewerRef.value.zoom(),
                rotate:  props.parentGeoViewerRef.value.rotation(),
                distanceToOutline: geo.util.distanceToPolygon2d(evt.mouse.geo, outlineFeature.data()[0]) / props.parentGeoViewerRef.value.unitsPerPixel(props.parentGeoViewerRef.value.zoom())
            };
        });
        featureLayer.geoOn(geo.event.actionmove, (evt: GeoEvent) => {
            switch (evt.state.action) {
                case 'overview_pan': {
                    if (!downState ){ //|| downState.distanceToOutline < -this._panOutlineDistance) {
                        return;
                    }
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
                    break;
            }
        });
        const onParentPan = () => {
          const parent = props.parentGeoViewerRef.value;
        if (parent.rotation() !== props.parentGeoViewerRef.value.rotation()) {
            props.parentGeoViewerRef.value.rotation(parent.rotation());
            props.parentGeoViewerRef.value.zoom(props.parentGeoViewerRef.value.zoom() - 1);
        }
        const size = parent.size();
        outlineFeature.style(outlineStyle);
        outlineFeature.data([[
            parent.displayToGcs({x: 0, y: 0}),
            parent.displayToGcs({x: size.width, y: 0}),
            parent.displayToGcs({x: size.width, y: size.height}),
            parent.displayToGcs({x: 0, y: size.height})
        ]]).draw();
        };
        onParentPan();
        // Bind parent pan to the outline feature
        props.parentGeoViewerRef.value.geoOn(geo.event.pan, onParentPan);
        polyLayerCreated.value = true;
    };
    watch(containerRef, () => {
      const { naturalWidth, naturalHeight } = props.image;
      if (containerRef.value) {
      geoJS.initializeViewer(containerRef.value, naturalWidth, naturalHeight, true);
      geoJS.drawImage(props.image, naturalWidth, naturalHeight);
      initialized.value = true;
        nextTick(() => createPolyLayer());
      }
    });


    return {
      containerRef,
      geoViewerRef: geoJS.getGeoViewer(),
      initialized,
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
      :other-user-annotations="otherUserAnnotations"
      :selected-id="selectedId"
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
