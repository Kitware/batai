<script lang="ts">
import { defineComponent, nextTick, onMounted, PropType, Ref, ref, watch } from "vue";
import { SpectrogramAnnotation } from "../../api/api";
import { geojsonToSpectro, SpectroInfo } from "./geoJSUtils";
import EditAnnotationLayer from "./layers/editAnnotationLayer";
import RectangleLayer from "./layers/rectangleLayer";
import LegendLayer from "./layers/legendLayer";
import TimeLayer from "./layers/timeLayer";
import FreqLayer from "./layers/freqLayer";
import SpeciesLayer from "./layers/speciesLayer";
import { cloneDeep } from "lodash";
import useState from "../../use/useState";
export default defineComponent({
  name: "LayerManager",
  props: {
    geoViewerRef: {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      type: Object as PropType<any>,
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
    thumbnail: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['selected', 'update:annotation', 'create:annotation', 'set-cursor', 'set-mode'],
  setup(props, { emit }) {
    const { annotationState, setAnnotationState, layerVisibility, } = useState();
    const selectedAnnotationId: Ref<null | number> = ref(null);
    const hoveredAnnotationId: Ref<null | number> = ref(null);
    const localAnnotations: Ref<SpectrogramAnnotation[]> = ref(cloneDeep(props.annotations));
    const editing = ref(false);
    const editingAnnotation: Ref<null | SpectrogramAnnotation> = ref(null);
    let rectAnnotationLayer: RectangleLayer;
    let editAnnotationLayer: EditAnnotationLayer;
    let legendLayer: LegendLayer;
    let timeLayer: TimeLayer;
    let freqLayer: FreqLayer;
    let speciesLayer: SpeciesLayer;
    const displayError = ref(false);
    const errorMsg = ref('');

    // eslint-disable-next-line @typescript-eslint/no-unused-vars, @typescript-eslint/no-explicit-any
    const event = (type: string, data: any) => {
      // Will handle clicking, selecting and editing here
      if (type === "update:mode") {
        emit('set-mode', data.mode);
        setAnnotationState(data.mode);
      }
      if (type === "update:cursor") {
        emit('set-cursor', data.cursor);
      }
      if (type === "annotation-cleared") {
        editing.value = false;
        selectedAnnotationId.value = null;
        editingAnnotation.value = null;
        editAnnotationLayer.disable();
        triggerUpdate();
        const copy: SpectrogramAnnotation[] = cloneDeep(localAnnotations.value);
        copy.forEach((item) => (item.editing = undefined));
        localAnnotations.value = copy;
        emit("selected", selectedAnnotationId.value);
      }
      if (type === "annotation-clicked") {
        if (selectedAnnotationId.value !== null) {
          const foundIndex = localAnnotations.value.findIndex(
            (item) => item.id === selectedAnnotationId.value
          );
          if (foundIndex !== -1) {
            editingAnnotation.value = localAnnotations.value[foundIndex];
            const copy: SpectrogramAnnotation[] = cloneDeep(localAnnotations.value);
            copy[foundIndex].editing = true;
            localAnnotations.value = copy;
          }
        }
        selectedAnnotationId.value = data.id;
        editing.value = data.edit;
        editingAnnotation.value = null;
        emit("selected", selectedAnnotationId.value);
        triggerUpdate();
      }
      if (type === "annotation-hover") {
        hoveredAnnotationId.value = data.id;
      }
      if (type === "annotation-right-clicked") {
        selectedAnnotationId.value = data.id;
        editing.value = data.edit;
        const foundIndex = localAnnotations.value.findIndex(
          (item) => item.id === selectedAnnotationId.value
        );
        if (editing.value && foundIndex !== -1) {
          editingAnnotation.value = localAnnotations.value[foundIndex];
          const copy: SpectrogramAnnotation[] = cloneDeep(localAnnotations.value);
          copy[foundIndex].editing = true;
          localAnnotations.value = copy;
        } else if (!editing.value && foundIndex !== -1) {
          editingAnnotation.value = null;
          localAnnotations.value[foundIndex].editing = undefined;
        }
        emit("selected", selectedAnnotationId.value);
        triggerUpdate();
      }
      if (type === "update:geojson") {
        const status = data["status"];
        const creating = data["creating"];
        const geoJSON = data["geoJSON"];
        if (geoJSON && selectedAnnotationId.value !== null && status === "editing" && !creating) {
          if (annotationState.value !== "creating") {
            const index = localAnnotations.value.findIndex(
              (item) => item.id === selectedAnnotationId.value
            );
            if (index !== -1 && props.spectroInfo) {
              // update bounds for the localAnnotation
              const conversionResult =  geojsonToSpectro(
                geoJSON,
                props.spectroInfo
              );
              if (conversionResult.error) {
                displayError.value = true;
                errorMsg.value = conversionResult.error;
                return;
              } 
              const { low_freq, high_freq, start_time, end_time } = conversionResult;
              localAnnotations.value[index] = {
                ...localAnnotations.value[index],
                low_freq,
                high_freq,
                start_time,
                end_time,
              };
              editingAnnotation.value = localAnnotations.value[index];
            }
            triggerUpdate();
            emit("update:annotation", editingAnnotation.value);
          }
        } else if (creating) {
          if (geoJSON && props.spectroInfo) {
            const conversionResult =  geojsonToSpectro(
                geoJSON,
                props.spectroInfo
              );

            if (conversionResult.error) {
                displayError.value = true;
                errorMsg.value = conversionResult.error;
                return;
              } 
            const { low_freq, high_freq, start_time, end_time } = conversionResult;
            const newAnnotation: SpectrogramAnnotation = {
              low_freq,
              high_freq,
              start_time,
              end_time,
              comments: "",
              species: [],
              id: 0,
            };
            emit("create:annotation", newAnnotation);
            editAnnotationLayer.disable();
            annotationState.value = '';
            editing.value = false;
          }
        }
      }
    };
    const triggerUpdate = () => {
      // Check for selected and editing annotations;
      if (rectAnnotationLayer) {
        rectAnnotationLayer.formatData(localAnnotations.value, selectedAnnotationId.value);
        rectAnnotationLayer.redraw();
      }
      if (!props.thumbnail) {
        if (layerVisibility.value.includes('grid')) {
          legendLayer.setGridEnabled(true);
        } else {
          legendLayer.setGridEnabled(false);
        }
        legendLayer.redraw();
        if (layerVisibility.value.includes('time')) {
          timeLayer.formatData(localAnnotations.value);
          timeLayer.redraw();
        } else {
          timeLayer.disable();
        }
        if (layerVisibility.value.includes('freq')) {
          freqLayer.formatData(localAnnotations.value);
          freqLayer.redraw();
        } else {
          freqLayer.disable();
        }
        if (layerVisibility.value.includes('species')) {
          speciesLayer.formatData(localAnnotations.value);
          speciesLayer.redraw();
        } else {
          speciesLayer.disable();
        }
      }
      if (editing.value && editingAnnotation.value) {
        setTimeout(() => {
          editAnnotationLayer.changeData(editingAnnotation.value);
        }, 0);
      }
    };
    watch(() => props.annotations, () => {
      localAnnotations.value = props.annotations;
      rectAnnotationLayer.formatData(localAnnotations.value, selectedAnnotationId.value);
      rectAnnotationLayer.redraw();
    });
    watch(
      () => props.selectedId,
      () => {
        selectedAnnotationId.value = props.selectedId;
        if (editAnnotationLayer && editAnnotationLayer.getMode() === 'editing' && props.selectedId === null) {
          nextTick(() => {
            if (editAnnotationLayer && editAnnotationLayer.getMode() === 'disabled' && props.selectedId === null) {
              emit('set-mode', 'disabled');
              editAnnotationLayer.featureLayer.clear();

            }
          });
          editAnnotationLayer.disable();
          return;
        }
        triggerUpdate();
      }
    );
    onMounted(() => {
      if (props.spectroInfo) {
        rectAnnotationLayer = new RectangleLayer(props.geoViewerRef, event, props.spectroInfo);
        editAnnotationLayer = new EditAnnotationLayer(props.geoViewerRef, event, props.spectroInfo);
        rectAnnotationLayer.formatData(localAnnotations.value, selectedAnnotationId.value);
        rectAnnotationLayer.redraw();
        if (!props.thumbnail) {
          legendLayer = new LegendLayer(props.geoViewerRef, event, props.spectroInfo);
          timeLayer = new TimeLayer(props.geoViewerRef, event, props.spectroInfo);
          timeLayer.formatData(localAnnotations.value);
          freqLayer = new FreqLayer(props.geoViewerRef, event, props.spectroInfo);
          freqLayer.formatData(localAnnotations.value);
          speciesLayer = new SpeciesLayer(props.geoViewerRef, event, props.spectroInfo);
          speciesLayer.formatData(localAnnotations.value);


          legendLayer.redraw();
          timeLayer.disable();
          freqLayer.disable();
          speciesLayer.disable();
        }
      }
    });
    watch(layerVisibility, () => {
      if (!props.thumbnail && legendLayer) {
        triggerUpdate();
      }
    });
    watch(
      () => annotationState.value,
      () => {
        if (annotationState.value === "creating") {
          editing.value = false;
          selectedAnnotationId.value = null;
          editingAnnotation.value = null;
          editAnnotationLayer.changeData(null);
          triggerUpdate();
        }
      }
    );
    return {
      annotationState,
      localAnnotations,
      displayError,
      errorMsg,
    };
  },
});
</script>

<template>
  <v-dialog
    v-model="displayError"
    width="500"
  >
    <v-card>
      <v-card-title>Error</v-card-title>
      <v-card-text>{{ errorMsg }}</v-card-text>
      <v-card-actions>
        <v-row>
          <v-spacer />
          <v-btn
            variant="outlined"
            @click="displayError=false;"
          >
            Dismiss
          </v-btn>
          <v-spacer />
        </v-row>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
./layers/timeLalyer