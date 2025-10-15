<script lang="ts">
import { defineComponent, nextTick, onMounted, onUnmounted, PropType, Ref, ref, watch } from "vue";
import * as d3 from "d3";
import { SpectrogramAnnotation, SpectrogramSequenceAnnotation } from "../../api/api";
import {
  annotationSpreadAcrossPulsesWarning,
  geojsonToSpectro,
  SpectroInfo,
  textColorFromBackground,
} from "./geoJSUtils";
import EditAnnotationLayer from "./layers/editAnnotationLayer";
import RectangleLayer from "./layers/rectangleLayer";
import CompressedOverlayLayer from "./layers/compressedOverlayLayer";
import SequenceLayer from "./layers/sequenceLayer";
import LegendLayer from "./layers/legendLayer";
import TimeLayer from "./layers/timeLayer";
import FreqLayer from "./layers/freqLayer";
import SpeciesLayer from "./layers/speciesLayer";
import SpeciesSequenceLayer from "./layers/speciesSequenceLayer";
import MeasureToolLayer from "./layers/measureToolLayer";
import BoundingBoxLayer from "./layers/boundingBoxLayer";
import AxesLayer from "./layers/axesLayer";
import { cloneDeep } from "lodash";
import useState from "@use/useState";
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
    yScale: {
      type: Number,
      default: 1,
    },
    scaledWidth: {
      type: Number,
      default: -1,
    },
    scaledHeight: {
      type: Number,
      default: -1,
    }
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
      sequenceAnnotations,
      otherUserAnnotations,
      selectedId,
      selectedType,
      setSelectedId,
      viewCompressedOverlay,
      configuration,
      colorScheme,
      backgroundColor,
      measuring,
      frequencyRulerY,
      drawingBoundingBox,
      boundingBoxError,
    } = useState();
    const selectedAnnotationId: Ref<null | number> = ref(null);
    const hoveredAnnotationId: Ref<null | number> = ref(null);
    const localAnnotations: Ref<SpectrogramAnnotation[]> = ref(cloneDeep(annotations.value));
    const localSequenceAnnotations: Ref<SpectrogramSequenceAnnotation[]> = ref(cloneDeep(sequenceAnnotations.value));
    const editing = ref(false);
    const editingAnnotation: Ref<null | SpectrogramAnnotation | SpectrogramSequenceAnnotation> = ref(null);
    let rectAnnotationLayer: RectangleLayer;
    let compressedOverlayLayer: CompressedOverlayLayer;
    let sequenceAnnotationLayer: SequenceLayer;
    let editAnnotationLayer: EditAnnotationLayer;
    let legendLayer: LegendLayer;
    let timeLayer: TimeLayer;
    let freqLayer: FreqLayer;
    let speciesLayer: SpeciesLayer;
    let speciesSequenceLayer: SpeciesSequenceLayer;
    let measureToolLayer: MeasureToolLayer;
    let boundingBoxLayer: BoundingBoxLayer;
    let axesLayer: AxesLayer;
    const displayError = ref(false);
    const errorMsg = ref("");

    // eslint-disable-next-line @typescript-eslint/no-unused-vars, @typescript-eslint/no-explicit-any
    const sequenceEvent = (type: string, data: any) => {
      if (type === "annotation-clicked") {
        // click sequence annotation
        if (selectedAnnotationId.value !== null) {
          const foundIndex = sequenceAnnotations.value.findIndex(
            (item) => item.id === selectedAnnotationId.value
          );
          if (foundIndex !== -1) {
            editingAnnotation.value = sequenceAnnotations.value[foundIndex];
            const copy: SpectrogramSequenceAnnotation[] = cloneDeep(localSequenceAnnotations.value);
            copy[foundIndex].editing = true;
            localSequenceAnnotations.value = copy;
          }
        }
        selectedAnnotationId.value = data.id;
        editing.value = data.edit;
        editingAnnotation.value = null;
        selectedId.value = selectedAnnotationId.value;
        if (data.id !== null) {
          setSelectedId(selectedAnnotationId.value, 'sequence');
        }
        setSelectedId(selectedAnnotationId.value);
        triggerUpdate();
      }
      if (type === "annotation-right-clicked") {
        selectedAnnotationId.value = data.id;
        editing.value = data.edit;
        const foundIndex = localSequenceAnnotations.value.findIndex(
          (item) => item.id === selectedAnnotationId.value
        );
        if (editing.value && foundIndex !== -1) {
          editingAnnotation.value = localSequenceAnnotations.value[foundIndex];
          const copy: SpectrogramSequenceAnnotation[] = cloneDeep(localSequenceAnnotations.value);
          copy[foundIndex].editing = true;
          localSequenceAnnotations.value = copy;
        } else if (!editing.value && foundIndex !== -1) {
          editingAnnotation.value = null;
          localSequenceAnnotations.value[foundIndex].editing = undefined;
        }
        if (data.id !== null) {
          setSelectedId(selectedAnnotationId.value, 'sequence');
        }
        setSelectedId(selectedAnnotationId.value);
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
        if (data.id !== null) {
          setSelectedId(selectedAnnotationId.value, 'pulse');
        }
        setSelectedId(selectedAnnotationId.value);
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
        if (data.id !== null) {
          setSelectedId(selectedAnnotationId.value, 'pulse');
        }
        setSelectedId(selectedAnnotationId.value);
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
            ) : localSequenceAnnotations.value.findIndex((item) => item.id === selectedAnnotationId.value);
            if (index !== -1 && props.spectroInfo && selectedType.value === 'pulse') {
              // update bounds for the localAnnotation
              const conversionResult = geojsonToSpectro(geoJSON, props.spectroInfo, props.scaledWidth, props.scaledHeight);
              if (conversionResult.warning) {
                displayError.value = true;
                errorMsg.value = conversionResult.warning;
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
              const conversionResult = geojsonToSpectro(geoJSON, props.spectroInfo, props.scaledWidth, props.scaledHeight);
              if (conversionResult.warning && conversionResult.warning !== annotationSpreadAcrossPulsesWarning) {
                displayError.value = true;
                errorMsg.value = conversionResult.warning;
                return;
              }
              const { start_time, end_time } = conversionResult;
              localSequenceAnnotations.value[index] = {
                ...localSequenceAnnotations.value[index],
                start_time,
                end_time,
              };
              editingAnnotation.value = localSequenceAnnotations.value[index];
            }

            triggerUpdate();
            emit("update:annotation", editingAnnotation.value);
          }
        } else if (creating) {
          if (geoJSON && props.spectroInfo) {
            const conversionResult = geojsonToSpectro(geoJSON, props.spectroInfo, props.scaledWidth, props.scaledHeight);

            if (conversionResult.warning
              && !(creationType.value === 'sequence' && conversionResult.warning === annotationSpreadAcrossPulsesWarning)
            ) {
              displayError.value = true;
              errorMsg.value = conversionResult.warning;
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
              const newAnnotation: SpectrogramSequenceAnnotation = {
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
      if (type === "measure:dragged") {
        const { yValue } = data;
        frequencyRulerY.value = yValue || 0;
      }
      if (type === "bbox:error") {
        const { error } = data;
        boundingBoxError.value = error || '';
      }
    };

    const getDataForLayers = () => {
      if (selectedUsers.value.length) {
        // We add more annotations to the system
        let additionalAnnotations: SpectrogramAnnotation[] = [];
        let additionalSequenceAnnotations: SpectrogramSequenceAnnotation[] = [];
        for (let i = 0; i < selectedUsers.value.length; i += 1) {
          const newAnnotations = otherUserAnnotations.value[selectedUsers.value[i]]['annotations'];
          additionalAnnotations = additionalAnnotations.concat(newAnnotations);
          const newSequenceAnnotations = otherUserAnnotations.value[selectedUsers.value[i]]['sequence'];
          additionalSequenceAnnotations = additionalSequenceAnnotations.concat(newSequenceAnnotations);

        }
        additionalAnnotations = additionalAnnotations.concat(localAnnotations.value);
        additionalSequenceAnnotations = additionalSequenceAnnotations.concat(localSequenceAnnotations.value);
        return { annotations: additionalAnnotations, sequenceAnnotations: additionalSequenceAnnotations, colorScale };
      } else {
        return { annotations: localAnnotations.value, sequenceAnnotations: localSequenceAnnotations.value };
      }
    };
    const triggerUpdate = () => {
      // Check for selected and editing annotations;
      const { annotations, sequenceAnnotations } = getDataForLayers();
      if (rectAnnotationLayer) {
        rectAnnotationLayer.formatData(
          annotations,
          selectedType.value === 'pulse' ? selectedAnnotationId.value : null,
          currentUser.value,
          colorScale.value,
          props.yScale,
        );
        rectAnnotationLayer.redraw();
      }
      if (viewCompressedOverlay.value && compressedOverlayLayer && !props.spectroInfo?.compressedWidth && props.spectroInfo?.start_times && props.spectroInfo.end_times) {
        compressedOverlayLayer.formatData(props.spectroInfo.start_times, props.spectroInfo.end_times, props.yScale);
        compressedOverlayLayer.redraw();
      } else {
        compressedOverlayLayer?.disable();
      }
      if (sequenceAnnotationLayer && layerVisibility.value.includes('sequence')) {
        sequenceAnnotationLayer.formatData(
          sequenceAnnotations,
          selectedType.value === 'sequence' ? selectedAnnotationId.value : null,
          currentUser.value,
          colorScale.value,
          props.yScale,
        );
        sequenceAnnotationLayer.redraw();
      }
      if (!props.thumbnail) {
        if (layerVisibility.value.includes("grid")) {
          legendLayer.setGridEnabled(true);
        } else {
          legendLayer.setGridEnabled(false);
        }
        legendLayer.redraw();
        if (layerVisibility.value.includes("time") || layerVisibility.value.includes('duration')) {
          if (layerVisibility.value.includes("time")) {
            timeLayer.displayDuration = false;
          } else {
            timeLayer.displayDuration = true;
          }
          timeLayer.formatData(annotations, sequenceAnnotations);
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
          speciesLayer.formatData(annotations);
          speciesLayer.redraw();
          speciesSequenceLayer.formatData(sequenceAnnotations);
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
      // We need to disable annotations that aren't required for different views
      if (!configuration.value.display_pulse_annotations) {
        rectAnnotationLayer?.disable();
        speciesLayer?.disable();
        freqLayer?.disable();
      }
      if (!configuration.value.display_sequence_annotations) {
        sequenceAnnotationLayer?.disable();
        speciesSequenceLayer?.disable();
      }
    };
    watch(
      annotations,
      () => {
        localAnnotations.value = annotations.value;
        triggerUpdate();
      }
    );
    watch(sequenceAnnotations, () => {
      localSequenceAnnotations.value = sequenceAnnotations.value;
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
    onUnmounted(() => {
      if (editAnnotationLayer) {
        editAnnotationLayer.destroy();
      }
      if (rectAnnotationLayer) {
        rectAnnotationLayer.destroy();
      }
      if (compressedOverlayLayer) {
        compressedOverlayLayer.destroy();
      }
      if (sequenceAnnotationLayer) {
        sequenceAnnotationLayer.destroy();
      }
      if (timeLayer) {
        timeLayer.destroy();
      }
      if (freqLayer) {
        freqLayer.destroy();
      }
      if (speciesLayer) {
        speciesLayer.destroy();
      }
      if (speciesSequenceLayer) {
        speciesSequenceLayer.destroy();
      }
    });
    const initLayers = () => {
      if (props.spectroInfo) {
        if (!compressedOverlayLayer) {
          compressedOverlayLayer = new CompressedOverlayLayer(props.geoViewerRef, props.spectroInfo);
        }
        compressedOverlayLayer.spectroInfo = props.spectroInfo;
        compressedOverlayLayer.setScaledDimensions(props.scaledWidth, props.scaledHeight);
        if (!editAnnotationLayer) {
          editAnnotationLayer = new EditAnnotationLayer(props.geoViewerRef, event, props.spectroInfo);
        }
        editAnnotationLayer.spectroInfo = props.spectroInfo;
        editAnnotationLayer.setScaledDimensions(props.scaledWidth, props.scaledHeight);
        if (!rectAnnotationLayer) {
          rectAnnotationLayer = new RectangleLayer(props.geoViewerRef, event, props.spectroInfo);
        }
        rectAnnotationLayer.spectroInfo = props.spectroInfo;
        rectAnnotationLayer.setScaledDimensions(props.scaledWidth, props.scaledHeight);

        if (!sequenceAnnotationLayer) {
          sequenceAnnotationLayer = new SequenceLayer(props.geoViewerRef, sequenceEvent, props.spectroInfo);
        } {
          sequenceAnnotationLayer.spectroInfo = props.spectroInfo;
          sequenceAnnotationLayer.setScaledDimensions(props.scaledWidth, props.scaledHeight);
        }
        rectAnnotationLayer.formatData(localAnnotations.value, selectedAnnotationId.value, currentUser.value, colorScale.value, props.yScale);
        rectAnnotationLayer.redraw();
        if (viewCompressedOverlay.value && compressedOverlayLayer && props.spectroInfo.start_times && props.spectroInfo.end_times) {
          compressedOverlayLayer.formatData(props.spectroInfo.start_times, props.spectroInfo.end_times, props.yScale);
          compressedOverlayLayer.redraw();
        }
        sequenceAnnotationLayer.formatData(localSequenceAnnotations.value, selectedAnnotationId.value, currentUser.value, colorScale.value, props.yScale);
        sequenceAnnotationLayer.redraw();
        if (!props.thumbnail) {
          if (!legendLayer) {
            legendLayer = new LegendLayer(props.geoViewerRef, event, props.spectroInfo);
          }
          legendLayer.spectroInfo = props.spectroInfo;
          legendLayer.createLabels();
          legendLayer.calcGridLines();
          legendLayer.setScaledDimensions(props.scaledWidth, props.scaledHeight);
          legendLayer.onPan();
          if (!timeLayer) {
            timeLayer = new TimeLayer(props.geoViewerRef, event, props.spectroInfo);
          }
          timeLayer.spectroInfo = props.spectroInfo;
          timeLayer.setScaledDimensions(props.scaledWidth, props.scaledHeight);
          if (!freqLayer) {
            freqLayer = new FreqLayer(props.geoViewerRef, event, props.spectroInfo);
          }
          freqLayer.spectroInfo = props.spectroInfo;
          freqLayer.setScaledDimensions(props.scaledWidth, props.scaledHeight);

          if (!speciesSequenceLayer) {
            speciesSequenceLayer = new SpeciesSequenceLayer(props.geoViewerRef, event, props.spectroInfo);
          }
          speciesSequenceLayer.spectroInfo = props.spectroInfo;
          speciesSequenceLayer.setScaledDimensions(props.scaledWidth, props.scaledHeight);
          if (!speciesLayer) {
            speciesLayer = new SpeciesLayer(props.geoViewerRef, event, props.spectroInfo);
          }
          speciesLayer.spectroInfo = props.spectroInfo;
          speciesLayer.setScaledDimensions(props.scaledWidth, props.scaledHeight);

          if (!measureToolLayer) {
            measureToolLayer = new MeasureToolLayer(
              props.geoViewerRef,
              event,
              props.spectroInfo,
              measuring.value,
              frequencyRulerY.value
            );
            measureToolLayer.setScaledDimensions(props.scaledWidth, props.scaledHeight);
          }
          measureToolLayer.redraw();
          watch(measuring, () => {
            if (measuring.value) {
              measureToolLayer.enableDrawing();
            } else {
              measureToolLayer.disableDrawing();
            }
          });

          if (!boundingBoxLayer) {
            boundingBoxLayer = new BoundingBoxLayer(props.geoViewerRef, event, props.spectroInfo, drawingBoundingBox.value);
            boundingBoxLayer.setScaledDimensions(props.scaledWidth, props.scaledHeight);
          }
          watch(drawingBoundingBox, () => {
            if (drawingBoundingBox.value) {
              boundingBoxLayer.enableDrawing();
            } else {
              boundingBoxLayer.disableDrawing();
            }
          });

          timeLayer.setDisplaying({ pulse: configuration.value.display_pulse_annotations, sequence: configuration.value.display_sequence_annotations });
          timeLayer.formatData(localAnnotations.value, sequenceAnnotations.value);
          freqLayer.formatData(localAnnotations.value);
          speciesLayer.formatData(localAnnotations.value);
          speciesSequenceLayer.formatData(localSequenceAnnotations.value);

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
        if (!props.thumbnail && !axesLayer) {
          axesLayer = new AxesLayer(props.geoViewerRef, event, props.spectroInfo);
          axesLayer.setScaledDimensions(props.scaledWidth, props.scaledHeight);
        }
        if (props.spectroInfo.compressedWidth && viewCompressedOverlay.value) {
          viewCompressedOverlay.value = false;
        }
      }
      triggerUpdate();
    };
    onMounted(() => {
      initLayers();
      updateColorFilter();
    });

    watch(() => props.spectroInfo, () => initLayers());
    watch(layerVisibility, () => {
      if (!props.thumbnail && legendLayer) {
        triggerUpdate();
      }
    });
    watch([() => props.scaledWidth, () => props.scaledHeight], () => {
      const { annotations, sequenceAnnotations } = getDataForLayers();
      if (legendLayer) {
        legendLayer.setScaledDimensions(props.scaledWidth, props.scaledHeight);
      }
      if (rectAnnotationLayer) {
        rectAnnotationLayer.setScaledDimensions(props.scaledWidth, props.scaledHeight);
        rectAnnotationLayer.formatData(
          annotations,
          selectedType.value === 'pulse' ? selectedAnnotationId.value : null,
          currentUser.value,
          colorScale.value,
          props.yScale,
        );
        rectAnnotationLayer.redraw();
      }
      if (compressedOverlayLayer && props.spectroInfo?.start_times && props.spectroInfo.end_times && viewCompressedOverlay.value) {
        if (!props.thumbnail && props.spectroInfo.compressedWidth ) {
          compressedOverlayLayer.setScaledDimensions(props.scaledWidth, props.scaledHeight);
          compressedOverlayLayer.formatData(props.spectroInfo.start_times, props.spectroInfo.end_times, props.yScale);
          compressedOverlayLayer.redraw();
        } else {
          compressedOverlayLayer?.disable();
        }
      }
      editAnnotationLayer?.setScaledDimensions(props.scaledWidth, props.scaledHeight);
      if (editing.value && editingAnnotation.value) {
        setTimeout(() => {
          editAnnotationLayer.changeData(editingAnnotation.value, selectedType.value);
        }, 0);
      }

      timeLayer?.setScaledDimensions(props.scaledWidth, props.scaledHeight);
      freqLayer?.setScaledDimensions(props.scaledWidth, props.scaledHeight);
      speciesLayer?.setScaledDimensions(props.scaledWidth, props.scaledHeight);
      speciesSequenceLayer?.setScaledDimensions(props.scaledWidth, props.scaledHeight);
      sequenceAnnotationLayer?.setScaledDimensions(props.scaledWidth, props.scaledHeight);
      if (timeLayer && (layerVisibility.value.includes("time") || layerVisibility.value.includes('duration'))) {
        if (layerVisibility.value.includes("time")) {
          timeLayer.displayDuration = false;
        } else {
          timeLayer.displayDuration = true;
        }
        timeLayer.formatData(annotations, sequenceAnnotations);
        timeLayer.redraw();
      }
      if (freqLayer && layerVisibility.value.includes("freq")) {
        freqLayer.formatData(annotations);
        freqLayer.redraw();
      } else {
        freqLayer?.disable();
      }
      if (speciesLayer && speciesSequenceLayer && layerVisibility.value.includes("species")) {
        speciesLayer.formatData(annotations);
        speciesLayer.redraw();
        speciesSequenceLayer.formatData(sequenceAnnotations);
        speciesSequenceLayer.redraw();
      } else {
        speciesLayer?.disable();
        speciesSequenceLayer?.disable();
      }
      if (sequenceAnnotationLayer && layerVisibility.value.includes('sequence')) {
        sequenceAnnotationLayer.formatData(
          sequenceAnnotations,
          selectedAnnotationId.value,
          currentUser.value,
          colorScale.value,
          props.yScale,
        );
        sequenceAnnotationLayer.redraw();
      }
      if (measureToolLayer) {
        measureToolLayer.setScaledDimensions(props.scaledWidth, props.scaledHeight);
        measureToolLayer.redraw();
      }
      // Triggers the Axis redraw when zoomed in and the axis is at the bottom/top
      legendLayer?.onPan();
      axesLayer?.setScaledDimensions(props.scaledWidth, props.scaledHeight);
    });
    watch(viewCompressedOverlay, () => {
      if (viewCompressedOverlay.value && compressedOverlayLayer && props.spectroInfo?.start_times && props.spectroInfo.end_times) {
        compressedOverlayLayer.setScaledDimensions(props.scaledWidth, props.scaledHeight);
        compressedOverlayLayer.formatData(props.spectroInfo.start_times, props.spectroInfo.end_times, props.yScale);
        compressedOverlayLayer.redraw();
      } else {
        compressedOverlayLayer.disable();
      }
    });
    watch(
      () => annotationState.value,
      () => {
        if (!props.thumbnail && annotationState.value === "creating") {
          editing.value = false;
          selectedAnnotationId.value = null;
          editingAnnotation.value = null;
          editAnnotationLayer.changeData(null, selectedType.value);
          triggerUpdate();
        }
      }
    );
    // Color scheme
    const rValues = ref('');
    const gValues = ref('');
    const bValues = ref('');

    function updateColorFilter() {
      if (!backgroundColor.value.includes(',')) {
        // convert rgb(0 0 0) to rgb(0, 0, 0)
        backgroundColor.value = backgroundColor.value.replace(/rgb\((\d+)\s+(\d+)\s+(\d+)\)/, 'rgb($1, $2, $3)');
      }

      const backgroundRgbColor = d3.color(backgroundColor.value) as d3.RGBColor;
      const redStops: number[] = [backgroundRgbColor.r / 255];
      const greenStops: number[] = [backgroundRgbColor.g / 255];
      const blueStops: number[] = [backgroundRgbColor.b / 255];
      for (let i = 0.1; i <= 1.0; i += 0.1) {
        const rgbStopString = colorScheme.value.scheme(i);
        const color = d3.color(rgbStopString) as d3.RGBColor;
        redStops.push(color.r / 255);
        greenStops.push(color.g / 255);
        blueStops.push(color.b / 255);
      }
      rValues.value = redStops.join(' ');
      gValues.value = greenStops.join(' ');
      bValues.value = blueStops.join(' ');
      const textColor = textColorFromBackground(backgroundColor.value);
      if (freqLayer) {
        freqLayer.setTextColor(textColor);
      }
      if (speciesLayer) {
        speciesLayer.setTextColor(textColor);
      }
      if (legendLayer) {
        legendLayer.setTextColor(textColor);
      }
      if (timeLayer) {
        timeLayer.setTextColor(textColor);
      }
      if (speciesSequenceLayer) {
        speciesSequenceLayer.setTextColor(textColor);
      }
      if (measureToolLayer) {
        measureToolLayer.setTextColor(textColor);
      }
      if (boundingBoxLayer) {
        boundingBoxLayer.setTextColor(textColor);
      }
    }

    watch([backgroundColor, colorScheme], updateColorFilter);

    return {
      annotationState,
      localAnnotations,
      displayError,
      errorMsg,
      selectedUsers,
      rValues,
      gValues,
      bValues,
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
  <svg
    width="0"
    height="0"
    style="position: absolute; top: -1px; left: -1px;"
  >
    <filter id="apply-color-scheme">
      <!-- convert to grayscale -->
      <feColorMatrix
        type="saturate"
        values="0"
        result="grayscale"
      />

      <!-- apply color scheme -->
      <feComponentTransfer>
        <feFuncR
          type="table"
          :tableValues="rValues"
        />
        <feFuncG
          type="table"
          :tableValues="gValues"
        />
        <feFuncB
          type="table"
          :tableValues="bValues"
        />
      </feComponentTransfer>
    </filter>
  </svg>
</template>
