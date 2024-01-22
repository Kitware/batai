<script lang="ts">
import { defineComponent, PropType, ref, Ref, watch } from "vue";
import { SpectroInfo, useGeoJS } from './geoJS/geoJSUtils';
import { SpectrogramAnnotation } from "../api/api";
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
  setup(props, { emit }) {
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
    }

    const createPolyLayer = () => {
      const geoViewer = geoJS.getGeoViewer();
      const featureLayer = geoViewer.value.createLayer('feature', {feattures: ['polygon']});
      const outlineFeature = featureLayer.createFeature('polygon', {
        style: {
          stroke: true,
          strokeCoor: 'yellow',
          strokeWidth: 1,
          fille: false,
        }
      });
      featureLayer.geoOn(geo.event.mouseclick, (evt: GeoEvent) => {
            props.parentGeoViewerRef.value.center(evt.geo);
      });
      featureLayer.geoOn(geo.event.actiondown, (evt) => {
            downState = {
                state: evt.state,
                mouse: evt.mouse,
                center:  props.parentGeoViewerRef.value.center(),
                zoom:  props.parentGeoViewerRef.value.zoom(),
                rotate:  props.parentGeoViewerRef.value.rotation(),
                //distanceToOutline: geo.util.distanceToPolygon2d(evt.mouse.geo, this._outlineFeature.data()[0]) / this.viewer.unitsPerPixel(this.viewer.zoom())
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
        polyLayerCreated.value = true;
    };
    watch(containerRef, () => {
      const { naturalWidth, naturalHeight } = props.image;
      if (containerRef.value)
      geoJS.initializeViewer(containerRef.value, naturalWidth, naturalHeight, true);
      geoJS.drawImage(props.image, naturalWidth, naturalHeight);
      initialized.value = true;
      if (!polyLayerCreated.value) {
        createPolyLayer();
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
      :selected-id="selectedId"
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
