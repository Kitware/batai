<script lang="ts">
import { defineComponent, PropType, ref, Ref, watch } from "vue";
import geo, { GeoEvent } from "geojs";
import { useGeoJS } from './geoJS/geoJSUtils';

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
    const geoJS = useGeoJS();

    watch(containerRef, () => {
      const { width, height } = props.image;
      if (containerRef.value)
      geoJS.initializeViewer(containerRef.value, width, height);
      geoJS.drawImage(props.image, width, height);
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
