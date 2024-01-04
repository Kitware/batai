<script lang="ts">
import { defineComponent, PropType, ref, Ref, watch } from "vue";
import geo, { GeoEvent } from "geojs";

export default defineComponent({
  name: "SpectroViewer",
  props: {
    image: {
      type: Object as PropType<HTMLImageElement>,
      required: true,
    },
  },
  setup(props) {
    const containerRef: Ref<HTMLElement | undefined> = ref();
    const geoViewer: Ref<any> = ref();
    let quadFeature: any;

    const initializeViewer = (width: number, height: number) => {
      if (containerRef.value) {
        const params = geo.util.pixelCoordinateParams(
         '#spectro',
          width,
          height
        );
        geoViewer.value = geo.map(params.map);
        const interactorOpts = geoViewer.value.interactor().options();
        interactorOpts.keyboard.focusHighlight = false;
        interactorOpts.keyboard.actions = {};
        interactorOpts.click.cancelOnMove = 5;

        interactorOpts.actions = [
          interactorOpts.actions[0],
          // The action below is needed to have GeoJS use the proper handler
          // with cancelOnMove for right clicks
          {
            action: geo.geo_action.select,
            input: { right: true },
            name: "button edit",
            owner: "geo.MapInteractor",
          },
          // The action below adds middle mouse button click to panning
          // It allows for panning while in the process of polygon editing or creation
          {
            action: geo.geo_action.pan,
            input: "middle",
            modifiers: { shift: false, ctrl: false },
            owner: "geo.mapInteractor",
            name: "button pan",
          },
          interactorOpts.actions[2],
          interactorOpts.actions[6],
          interactorOpts.actions[7],
          interactorOpts.actions[8],
          interactorOpts.actions[9],
        ];
        // Set > 2pi to disable rotation
        interactorOpts.zoomrotateMinimumRotation = 7;
        interactorOpts.zoomAnimation = {
          enabled: false,
        };
        interactorOpts.momentum = {
          enabled: false,
        };
        interactorOpts.wheelScaleY = 0.2;
        geoViewer.value.interactor().options(interactorOpts);
        geoViewer.value.bounds({
            left: 0,
            top: 0,
            bottom: height,
            right: width,
        });

        const quadFeatureLayer = geoViewer.value.createLayer("feature", {
          features: ["quad"],
          autoshareRenderer: false,
          renderer: "canvas",
        });
        quadFeature = quadFeatureLayer.createFeature("quad");
      }
    };
    watch(containerRef, () => {
      const { width, height } = props.image;
      initializeViewer(width, height);
      // Draw Image
      if (quadFeature) {
        quadFeature
          .data([
            {
              ul: { x: 0, y: 0 },
              lr: { x: width, y: height },
              image: props.image,
            },
          ])
          .draw();
      }
    });

    return {
      containerRef,
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
  width:100vw;
  height: 100vh;

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
