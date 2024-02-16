<script lang="ts">
import { defineComponent, nextTick, onMounted, PropType, Ref, ref, watch } from "vue";
import { SpectrogramAnnotation, SpectrogramTemporalAnnotation } from "../../api/api";
import { geojsonToSpectro, SpectroInfo } from "./geoJSUtils";
import EditAnnotationLayer from "./layers/editAnnotationLayer";
import RectangleLayer from "./layers/rectangleLayer";
import TemporalLayer from "./layers/temporalLayer";
import LegendLayer from "./layers/legendLayer";
import TimeLayer from "./layers/timeLayer";
import FreqLayer from "./layers/freqLayer";
import SpeciesLayer from "./layers/speciesLayer";
import SpeciesSequenceLayer from "./layers/speciesSequenceLayer";
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
    thumbnail: {
      type: Boolean,
      default: false,
    },
  },
  emits: ["selected", "update:annotation", "create:annotation", "set-cursor"],
  setup(props, { emit }) {
    const {
      creationType,
      annotationState,
      setAnnotationState,
      layerVisibility,
      selectedUsers,
      colorScale,
      currentUser,
      annotations,
      temporalAnnotations,
      otherUserAnnotations,
      selectedId,
      selectedType,
      setSelectedId,
    } = useState();
    const selectedAnnotationId: Ref<null | number> = ref(null);
    const hoveredAnnotationId: Ref<null | number> = ref(null);
    const localAnnotations: Ref<SpectrogramAnnotation[]> = ref(cloneDeep(annotations.value));
    const localTemporalAnnotations: Ref<SpectrogramTemporalAnnotation[]> = ref(cloneDeep(temporalAnnotations.value));
    const editing = ref(false);
    const editingAnnotation: Ref<null | SpectrogramAnnotation | SpectrogramTemporalAnnotation> = ref(null);
    let rectAnnotationLayer: RectangleLayer;
    let temporalAnnotationLayer: TemporalLayer;
    let editAnnotationLayer: EditAnnotationLayer;
    let legendLayer: LegendLayer;
    let timeLayer: TimeLayer;
    let freqLayer: FreqLayer;
    let speciesLayer: SpeciesLayer;
    let speciesSequenceLayer: SpeciesSequenceLayer;
    const displayError = ref(false);
    const errorMsg = ref("");

    // eslint-disable-next-line @typescript-eslint/no-unused-vars, @typescript-eslint/no-explicit-any
    const temporalEvent = (type: string, data: any) => {
      if (type === "annotation-clicked") {
        // click temporal annotation
        if (selectedAnnotationId.value !== null) {
          const foundIndex = temporalAnnotations.value.findIndex(
            (item) => item.id === selectedAnnotationId.value
          );
          if (foundIndex !== -1) {
            editingAnnotation.value = temporalAnnotations.value[foundIndex];
            const copy: SpectrogramTemporalAnnotation[] = cloneDeep(localTemporalAnnotations.value);
            copy[foundIndex].editing = true;
            localTemporalAnnotations.value = copy;
          }
        }
        selectedAnnotationId.value = data.id;
        editing.value = data.edit;
        editingAnnotation.value = null;
        selectedId.value = selectedAnnotationId.value;
        //emit("selected", selectedAnnotationId.value);
        setSelectedId(selectedAnnotationId.value, 'sequence');
        triggerUpdate();
      }
      if (type === "annotation-right-clicked") {
        selectedAnnotationId.value = data.id;
        editing.value = data.edit;
        const foundIndex = localTemporalAnnotations.value.findIndex(
          (item) => item.id === selectedAnnotationId.value
        );
        if (editing.value && foundIndex !== -1) {
          editingAnnotation.value = localTemporalAnnotations.value[foundIndex];
          const copy: SpectrogramTemporalAnnotation[] = cloneDeep(localTemporalAnnotations.value);
          copy[foundIndex].editing = true;
          localTemporalAnnotations.value = copy;
        } else if (!editing.value && foundIndex !== -1) {
          editingAnnotation.value = null;
          localTemporalAnnotations.value[foundIndex].editing = undefined;
        }
        setSelectedId(selectedAnnotationId.value, 'sequence');
        //emit("selected", selectedAnnotationId.value);
        triggerUpdate();
      }

    };

    // eslint-disable-next-line @typescript-eslint/no-unused-vars, @typescript-eslint/no-explicit-any
    const event = (type: string, data: any) => {
      // Will handle clicking, selecting and editing here
      if (type === "update:mode") {
        setAnnotationState(data.mode);
      }
      if (type === "update:cursor") {
        emit("set-cursor", data.cursor);
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
        setSelectedId(selectedAnnotationId.value, 'pulse');
        //emit("selected", selectedAnnotationId.value);
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
        selectedId.value = selectedAnnotationId.value;
        //emit("selected", selectedAnnotationId.value);
        setSelectedId(selectedAnnotationId.value, 'pulse');
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
        setSelectedId(selectedAnnotationId.value, 'pulse');
        //emit("selected", selectedAnnotationId.value);
        triggerUpdate();
      }
      if (type === "update:geojson") {
        const status = data["status"];
        const creating = data["creating"];
        const geoJSON = data["geoJSON"];
        if (geoJSON && selectedAnnotationId.value !== null && status === "editing" && !creating) {
          if (annotationState.value !== "creating") {
            const index = selectedType.value === 'pulse' ? localAnnotations.value.findIndex(
              (item) => item.id === selectedAnnotationId.value
            ) : localTemporalAnnotations.value.findIndex((item) => item.id === selectedAnnotationId.value);
            if (index !== -1 && props.spectroInfo && selectedType.value === 'pulse') {
              // update bounds for the localAnnotation
              const conversionResult = geojsonToSpectro(geoJSON, props.spectroInfo);
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
            if (index !== -1 && props.spectroInfo && selectedType.value === 'sequence') {
              // update bounds for the localAnnotation
              const conversionResult = geojsonToSpectro(geoJSON, props.spectroInfo);
              if (conversionResult.error) {
                displayError.value = true;
                errorMsg.value = conversionResult.error;
                return;
              }
              const { start_time, end_time } = conversionResult;
              localTemporalAnnotations.value[index] = {
                ...localTemporalAnnotations.value[index],
                start_time,
                end_time,
              };
              editingAnnotation.value = localTemporalAnnotations.value[index];
            }

            triggerUpdate();
            emit("update:annotation", editingAnnotation.value);
          }
        } else if (creating) {
          if (geoJSON && props.spectroInfo) {
            const conversionResult =  geojsonToSpectro(geoJSON, props.spectroInfo);

            if (conversionResult.error) {
              displayError.value = true;
              errorMsg.value = conversionResult.error;
              return;
            }
            const { low_freq, high_freq, start_time, end_time } = conversionResult;
            if (creationType.value === 'pulse') {
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
          } else if (creationType.value === 'sequence') {
            const newAnnotation: SpectrogramTemporalAnnotation = {
                start_time,
                end_time,
                species: [],
                type: '',
                comments: '',
                id: 0,
              };
              emit("create:annotation", newAnnotation);

          }
            editAnnotationLayer.disable();
            annotationState.value = "";
            editing.value = false;
          }
        }
      }
    };

    const getDataForLayers = () => {
      if (selectedUsers.value.length) {
        // We add more annotations to the system
        let additionalAnnotations: SpectrogramAnnotation[] = [];
        for (let i = 0; i < selectedUsers.value.length; i += 1) {
          const newAnnotations = otherUserAnnotations.value[selectedUsers.value[i]];
          additionalAnnotations = additionalAnnotations.concat(newAnnotations);
        }
        additionalAnnotations = additionalAnnotations.concat(localAnnotations.value);
        return { annotations: additionalAnnotations, temporalAnnotations: localTemporalAnnotations.value, colorScale };
      } else {
        return { annotations: localAnnotations.value, temporalAnnotations: localTemporalAnnotations.value };
      }
    };
    const triggerUpdate = () => {
      // Check for selected and editing annotations;
      const { annotations, temporalAnnotations } = getDataForLayers();
      if (rectAnnotationLayer) {
        rectAnnotationLayer.formatData(
          annotations,
          selectedType.value === 'pulse' ? selectedAnnotationId.value : null,
          currentUser.value,
          colorScale.value
        );
        rectAnnotationLayer.redraw();
      }
      if (temporalAnnotationLayer && layerVisibility.value.includes('temporal')) {
        temporalAnnotationLayer.formatData(
          temporalAnnotations,
          selectedType.value === 'sequence' ? selectedAnnotationId.value : null,
          currentUser.value,
          colorScale.value
        );
        temporalAnnotationLayer.redraw();
      }
      if (!props.thumbnail) {
        if (layerVisibility.value.includes("grid")) {
          legendLayer.setGridEnabled(true);
        } else {
          legendLayer.setGridEnabled(false);
        }
        legendLayer.redraw();
        if (layerVisibility.value.includes("time")) {
          timeLayer.formatData(annotations, temporalAnnotations);
          timeLayer.redraw();
        } else {
          timeLayer.disable();
        }
        if (layerVisibility.value.includes("freq")) {
          freqLayer.formatData(annotations);
          freqLayer.redraw();
        } else {
          freqLayer.disable();
        }
        if (layerVisibility.value.includes("species")) {
          speciesLayer.formatData(localAnnotations.value);
          speciesLayer.redraw();
          speciesSequenceLayer.formatData(localTemporalAnnotations.value);
          speciesSequenceLayer.redraw();
        } else {
          speciesLayer.disable();
          speciesSequenceLayer.disable();
        }
      }
      if (editing.value && editingAnnotation.value) {
        setTimeout(() => {
          editAnnotationLayer.changeData(editingAnnotation.value, selectedType.value);
        }, 0);
      }
    };
    watch(
      annotations,
      () => {
        localAnnotations.value = annotations.value;
        triggerUpdate();
      }
    );
    watch (temporalAnnotations, () => {
      localTemporalAnnotations.value = temporalAnnotations.value;
      triggerUpdate();
    });
    watch(selectedUsers, () => triggerUpdate());
    watch(
      selectedId,
      () => {
        selectedAnnotationId.value = selectedId.value;
        if (
          editAnnotationLayer &&
          editAnnotationLayer.getMode() === "editing" &&
          selectedId.value === null
        ) {
          nextTick(() => {
            if (
              editAnnotationLayer &&
              editAnnotationLayer.getMode() === "disabled" &&
              selectedId.value === null
            ) {
              annotationState.value === 'disabled';
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
        editAnnotationLayer = new EditAnnotationLayer(props.geoViewerRef, event, props.spectroInfo);
        rectAnnotationLayer = new RectangleLayer(props.geoViewerRef, event, props.spectroInfo);
        rectAnnotationLayer.formatData(localAnnotations.value, selectedAnnotationId.value, currentUser.value, colorScale.value);
        rectAnnotationLayer.redraw();
        temporalAnnotationLayer = new TemporalLayer(props.geoViewerRef, temporalEvent, props.spectroInfo);
        temporalAnnotationLayer.formatData(localTemporalAnnotations.value, selectedAnnotationId.value, currentUser.value, colorScale.value);
        temporalAnnotationLayer.redraw();
        if (!props.thumbnail) {
          legendLayer = new LegendLayer(props.geoViewerRef, event, props.spectroInfo);
          timeLayer = new TimeLayer(props.geoViewerRef, event, props.spectroInfo);
          timeLayer.formatData(localAnnotations.value, temporalAnnotations.value);
          freqLayer = new FreqLayer(props.geoViewerRef, event, props.spectroInfo);
          freqLayer.formatData(localAnnotations.value);
          speciesLayer = new SpeciesLayer(props.geoViewerRef, event, props.spectroInfo);
          speciesLayer.formatData(localAnnotations.value);
          speciesSequenceLayer = new SpeciesSequenceLayer(props.geoViewerRef, event, props.spectroInfo);
          speciesSequenceLayer.formatData(localTemporalAnnotations.value);

          legendLayer.redraw();
          if (layerVisibility.value.includes('species')) {
            speciesLayer.redraw();
            speciesSequenceLayer.redraw();
          } else {
            speciesLayer.disable();
            speciesSequenceLayer.disable();
          }
          timeLayer.disable();
          freqLayer.disable();
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
          editAnnotationLayer.changeData(null, selectedType.value);
          triggerUpdate();
        }
      }
    );
    return {
      annotationState,
      localAnnotations,
      displayError,
      errorMsg,
      selectedUsers,
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
            @click="displayError = false"
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
