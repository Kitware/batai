<script lang="ts">
import maplibregl, { type GeoJSONSource, type Map } from 'maplibre-gl';
import { defineComponent, onBeforeUnmount, onMounted, ref, watch, type PropType } from 'vue';
import { getRecordingLocations, type RecordingLocationsGeoJson } from '@api/api';

export default defineComponent({
  name: 'RecordingLocationsMap',
  props: {
    height: {
      type: [Number, String] as PropType<number | string>,
      default: 600,
    },
    tags: {
      type: Array as PropType<string[]>,
      default: () => [],
    },
    excludeSubmitted: {
      type: Boolean,
      default: false,
    },
    resizeTick: {
      type: Number,
      default: 0,
    },
    /** When true, emit current map bounds (debounced on pan/zoom; immediate when enabled). */
    reportBounds: {
      type: Boolean,
      default: false,
    },
    boundsDebounceMs: {
      type: Number,
      default: 1500,
    },
    /** Optional bounds to restore the map viewport (west,south,east,north). */
    initialBounds: {
      type: Array as unknown as PropType<[number, number, number, number] | null>,
      default: null,
    },
  },
  emits: ['boundsChange'],
  setup(props, { emit }) {
    const mapContainer = ref<HTMLDivElement | null>(null);
    const mapRef = ref<Map | null>(null);
    const loading = ref(false);
    const error = ref<string | null>(null);
    let boundsDebounceTimer: ReturnType<typeof setTimeout> | null = null;

    function clearBoundsDebounce() {
      if (boundsDebounceTimer !== null) {
        clearTimeout(boundsDebounceTimer);
        boundsDebounceTimer = null;
      }
    }

    function emitCurrentBounds() {
      if (!props.reportBounds || !mapRef.value) return;
      const b = mapRef.value.getBounds();
      emit('boundsChange', [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()] as [
        number,
        number,
        number,
        number,
      ]);
    }

    function scheduleDebouncedBounds() {
      if (!props.reportBounds) return;
      clearBoundsDebounce();
      boundsDebounceTimer = setTimeout(() => {
        boundsDebounceTimer = null;
        emitCurrentBounds();
      }, props.boundsDebounceMs);
    }

    async function loadGeoJson(): Promise<RecordingLocationsGeoJson> {
      const res = await getRecordingLocations({
        exclude_submitted: props.excludeSubmitted ? true : undefined,
        tags: props.tags.length ? props.tags : undefined,
      });
      return res.data;
    }

    async function refreshSource() {
      if (!mapRef.value) return;
      const src = mapRef.value.getSource('recording-locations') as GeoJSONSource | undefined;
      if (!src) return;
      loading.value = true;
      error.value = null;
      try {
        const data = await loadGeoJson();
        src.setData(data as unknown as GeoJSON.GeoJSON);
      } catch (e) {
        error.value = e instanceof Error ? e.message : String(e);
      } finally {
        loading.value = false;
      }
    }

    onMounted(async () => {
      if (!mapContainer.value) return;

      // Center roughly on the continental US.
      const map = new maplibregl.Map({
        container: mapContainer.value,
        style: {
          version: 8,
          sources: {
            osm: {
              type: 'raster',
              tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
              tileSize: 256,
              attribution: '&copy; OpenStreetMap contributors',
            },
          },
          layers: [
            {
              id: 'osm',
              type: 'raster',
              source: 'osm',
            },
          ],
        },
        center: [-98.5795, 39.8283],
        zoom: 3,
        fadeDuration: 0,
      });
      mapRef.value = map;

      map.addControl(new maplibregl.NavigationControl(), 'top-right');

      map.on('load', async () => {
        loading.value = true;
        error.value = null;
        try {
          const data = await loadGeoJson();

          map.addSource('recording-locations', {
            type: 'geojson',
            data: data as unknown as GeoJSON.GeoJSON,
            cluster: true,
            clusterMaxZoom: 14,
            clusterRadius: 50,
          });

          map.addLayer({
            id: 'clusters',
            type: 'circle',
            source: 'recording-locations',
            filter: ['has', 'point_count'],
            paint: {
              'circle-color': [
                'step',
                ['get', 'point_count'],
                '#51bbd6',
                100,
                '#f1f075',
                750,
                '#f28cb1',
              ],
              'circle-radius': [
                'step',
                ['get', 'point_count'],
                20,
                100,
                30,
                750,
                40,
              ],
              'circle-stroke-width': 1,
              'circle-stroke-color': '#ffffff',
            },
          });

          map.addLayer({
            id: 'cluster-count',
            type: 'symbol',
            source: 'recording-locations',
            filter: ['has', 'point_count'],
            layout: {
              'text-field': '{point_count_abbreviated}',
              'text-size': 12,
            },
            paint: {
              'text-color': '#0b1f2a',
            },
          });

          map.addLayer({
            id: 'unclustered-point',
            type: 'circle',
            source: 'recording-locations',
            filter: ['!', ['has', 'point_count']],
            paint: {
              'circle-color': '#11b4da',
              'circle-radius': 5,
              'circle-stroke-width': 1,
              'circle-stroke-color': '#fff',
            },
          });

          map.on('click', 'clusters', async (e) => {
            const features = map.queryRenderedFeatures(e.point, { layers: ['clusters'] });
            const f = features?.[0];
            if (!f) return;
            const clusterId = (f.properties as Record<string, unknown>)?.cluster_id as number | undefined;
            if (clusterId === undefined) return;
            const source = map.getSource('recording-locations') as GeoJSONSource;
            const zoom = await source.getClusterExpansionZoom(clusterId);
            const coords = (f.geometry as GeoJSON.Point).coordinates as [number, number];
            map.easeTo({ center: coords, zoom });
          });

          map.on('click', 'unclustered-point', (e) => {
            const f = e.features?.[0];
            if (!f) return;
            const coords = (f.geometry as GeoJSON.Point).coordinates.slice() as [number, number];
            const props = (f.properties ?? {}) as Record<string, unknown>;
            const recordingId = props.recording_id ?? '';
            const filename = props.filename ?? '';

            new maplibregl.Popup()
              .setLngLat(coords)
              .setHTML(
                `<div style="font-size: 12px;">
                  <div><b>Recording ID:</b> ${recordingId}</div>
                  <div style="word-break: break-word;"><b>File:</b> ${filename}</div>
                </div>`
              )
              .addTo(map);
          });

          map.on('mouseenter', 'clusters', () => (map.getCanvas().style.cursor = 'pointer'));
          map.on('mouseleave', 'clusters', () => (map.getCanvas().style.cursor = ''));
          map.on('mouseenter', 'unclustered-point', () => (map.getCanvas().style.cursor = 'pointer'));
          map.on('mouseleave', 'unclustered-point', () => (map.getCanvas().style.cursor = ''));

          // If we have saved bounds, align the viewport before emitting the current bounds.
          if (props.initialBounds) {
            const [west, south, east, north] = props.initialBounds;
            if ([west, south, east, north].every((n) => Number.isFinite(n))) {
              map.fitBounds(
                [
                  [west, south],
                  [east, north],
                ],
                { padding: 20, duration: 0 },
              );
            }
          }

          map.on('moveend', () => {
            scheduleDebouncedBounds();
          });
          if (props.reportBounds) {
            emitCurrentBounds();
          }
        } catch (e) {
          error.value = e instanceof Error ? e.message : String(e);
        } finally {
          loading.value = false;
        }
      });
    });

    watch(
      () => [props.tags.join(','), props.excludeSubmitted] as const,
      async () => {
        await refreshSource();
      }
    );

    watch(
      () => props.resizeTick,
      () => {
        mapRef.value?.resize();
      }
    );

    watch(
      () => props.reportBounds,
      (on) => {
        if (on) {
          emitCurrentBounds();
        } else {
          clearBoundsDebounce();
        }
      }
    );

    onBeforeUnmount(() => {
      clearBoundsDebounce();
      mapRef.value?.remove();
      mapRef.value = null;
    });

    return { mapContainer, loading, error };
  },
});
</script>

<template>
  <div class="recording-locations-map-root">
    <div
      ref="mapContainer"
      class="recording-locations-map"
      :style="{ height: typeof height === 'number' ? `${height}px` : height }"
    />
    <div
      v-if="loading"
      class="status-overlay"
    >
      Loading locations…
    </div>
    <div
      v-else-if="error"
      class="status-overlay error"
    >
      {{ error }}
    </div>
  </div>
</template>

<style scoped>
.recording-locations-map-root {
  position: relative;
  width: 100%;
}
.recording-locations-map {
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
}
.status-overlay {
  position: absolute;
  left: 12px;
  bottom: 12px;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.65);
  color: white;
  font-size: 12px;
}
.status-overlay.error {
  background: rgba(120, 0, 0, 0.75);
}
</style>

