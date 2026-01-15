<!-- eslint-disable @typescript-eslint/no-explicit-any -->
<script lang="ts">
import { defineComponent, PropType, Ref, ref, onMounted } from "vue";
import { watch } from "vue";
import { getCellBbox } from "@api/api";
import geo, { GeoEvent } from "geojs";

export default defineComponent({
  name: "MapLocation",
  components: {},
  props: {
    editor: {
      type: Boolean,
      default: true,
    },
    size: {
      type: Object as PropType<{ width: number; height: number }>,
      default: () => ({ width: 300, height: 300 }),
    },
    location: {
      type: Object as PropType<{ x?: number; y?: number } | undefined>,
      default: () => undefined,
    },
    grtsCellId: {
      type: Number,
      default: undefined,
    },
    updateMap: {
      type: Number,
      default: 0,
    },
  },
  emits: ['location'],
  setup(props, { emit }) {
    const usCenter = { x: -90.5855, y: 39.8333 };
    const mapRef: Ref<HTMLDivElement | null> = ref(null);
    const map: Ref<any> = ref();
    const mapLayer: Ref<any> = ref();
    const markerLayer: Ref<any> = ref();
    const bboxLayer: Ref<any> = ref();
    const markerFeature: Ref<any> = ref();
    const bboxFeature: Ref<any> = ref();
    const markerLocation: Ref<{ x: number; y: number } | null> = ref(null);
    const uiLayer: Ref<any> = ref();
    const mounted = ref(false);

    onMounted(async () => {
      mounted.value = true;
    });
    watch(mapRef, async () => {
      if (mapRef.value) {
        const centerPoint = props.location && props.location.x && props.location.y ? props.location : usCenter;
        const zoomLevel = props.location && props.location.x && props.location.y ? 6 : 3;
        map.value = geo.map({ node: mapRef.value, center: centerPoint, zoom: zoomLevel });
        mapLayer.value = map.value.createLayer("osm");
        markerLayer.value = map.value.createLayer("feature", { features: ["marker"] });
        bboxLayer.value = map.value.createLayer("feature", { features: ["polygon"] });
        uiLayer.value = map.value.createLayer("ui");
        markerFeature.value = markerLayer.value.createFeature("marker");
        bboxFeature.value = bboxLayer.value.createFeature("polygon");
        uiLayer.value.createWidget('slider');
        uiLayer.value.createWidget('scale', {
          position: { bottom: 10, left: 10},
        });


        if (props.grtsCellId !== undefined) {
          const annotation = await getCellBbox(props.grtsCellId);
          const coordinates = annotation.data.geometry.coordinates;
          const data = coordinates.map((point: number[]) => ({ x: point[0], y: point[1] }));
          data.push({ x: coordinates[0][0], y: coordinates[0][1] });
          bboxFeature.value.data([data]).style({
            stroke: true,
            strokeWidth: 1,
            strokeColor: 'black',
            fill: false,
          }).draw();
          bboxLayer.value.draw();
          const center = {
            x: (data[0].x + data[2].x) / 2,
            y: (data[0].y + data[1].y) / 2
          };
          map.value.center(center);
          map.value.zoom(9);
        } else if (props.location?.x && props.location?.y) {
            markerLocation.value = { x: props.location?.x, y: props.location.y };
            markerFeature.value
              .data([markerLocation.value])
              .style({
                symbol: geo.markerFeature.symbols.drop,
                symbolValue: 1 / 3,
                rotation: -Math.PI / 2,
                radius: 30,
                strokeWidth: 5,
                strokeColor: "blue",
                fillColor: "yellow",
                rotateWithMap: false,
              })
              .draw();
        }
        if (props.editor) {
          mapLayer.value.geoOn(geo.event.mouseclick, (e: GeoEvent) => {
            // Place a marker at the point
            const { x, y } = e.geo;
            markerLocation.value = { x, y };
            markerFeature.value
              .data([markerLocation.value])
              .style({
                symbol: geo.markerFeature.symbols.drop,
                symbolValue: 1 / 3,
                rotation: -Math.PI / 2,
                radius: 30,
                strokeWidth: 5,
                strokeColor: "blue",
                fillColor: "yellow",
                rotateWithMap: false,
              })
              .draw();
              emit('location', { lon: x, lat:y });

          });
        }
      }
    });
    watch(() =>  props.updateMap, () => {
      if (props.location?.x && props.location?.y) {
            markerLocation.value = { x: props.location?.x, y: props.location.y };
            markerFeature.value
              .data([markerLocation.value])
              .style({
                symbol: geo.markerFeature.symbols.drop,
                symbolValue: 1 / 3,
                rotation: -Math.PI / 2,
                radius: 30,
                strokeWidth: 5,
                strokeColor: "blue",
                fillColor: "yellow",
                rotateWithMap: false,
              })
              .draw();
              const zoomLevel = props.location && props.location.x && props.location.y ? 6 : 3;
              const centerPoint = props.location && props.location.x && props.location.y ? props.location : usCenter;
              if (map.value) {
                map.value.zoom(zoomLevel);
                map.value.center(centerPoint);
              }

        }
    });
    return {
      mapRef,
    };
  },
});
</script>

<template>
  <v-card class="pa-0 ma-0">
    <div
      ref="mapRef"
      :style="`width:${size.width}px; height:${size.height}px`"
    />
  </v-card>
</template>

<style lang="scss" scoped></style>
