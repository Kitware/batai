<script lang="ts">
import { defineComponent, onMounted, PropType, Ref, ref, watch } from "vue";
import { SpectrogramAnnotation } from "../../api/api";
import { geojsonToSpectro, SpectroInfo } from "./geoJSUtils";
import EditAnnotationLayer from "./layers/editAnnotationLayer";
import RectangleLayer from "./layers/rectangleLayer";
import { cloneDeep } from "lodash";
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
    }
  },
  setup(props, { emit }) {
    const selectedAnnotationId: Ref<null | number> = ref(null);
    const hoveredAnnotationId: Ref<null | number> = ref(null);
    const localAnnotations: Ref<SpectrogramAnnotation[]> = ref(cloneDeep(props.annotations));
    const editing = ref(false);
    const editingAnnotation: Ref<null | SpectrogramAnnotation> = ref(null);
    let rectAnnotationLayer: RectangleLayer;
    let editAnnotationLayer: EditAnnotationLayer;
    // eslint-disable-next-line @typescript-eslint/no-unused-vars, @typescript-eslint/no-explicit-any
    const event = (type: string, data: any) => {
      // Will handle clicking, selecting and editing here
      if (type === "annotation-cleared") {
        editing.value = false;
        selectedAnnotationId.value = null;
        editingAnnotation.value = null;
        editAnnotationLayer.disable();
        triggerUpdate();
        const copy: SpectrogramAnnotation[] = cloneDeep(localAnnotations.value);
        copy.forEach((item) => (item.editing = undefined));
        localAnnotations.value = copy;
        emit('selected', selectedAnnotationId.value);

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
        emit('selected', selectedAnnotationId.value);
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
        emit('selected', selectedAnnotationId.value);
        triggerUpdate();
      }
      if (type === 'update:geojson') {
        const status = data['status'];
        const creating = data['creating'];
        const geoJSON = data['geoJSON'];
        if (geoJSON && selectedAnnotationId.value !== null && status === 'editing' && !creating) {
            const index = localAnnotations.value.findIndex((item) => item.id === selectedAnnotationId.value);
            if (index !== -1 && props.spectroInfo) {
                // update bounds for the localAnnotation
                const { low_freq, high_freq, start_time, end_time } = geojsonToSpectro(geoJSON, props.spectroInfo);
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
            emit('update:annotaton', {annotation: editingAnnotation.value });
        }
      }
    };
    const triggerUpdate = () => {
      // Check for selected and editing annotations;
      if (rectAnnotationLayer) {
        rectAnnotationLayer.formatData(localAnnotations.value, selectedAnnotationId.value);
        rectAnnotationLayer.redraw();
      }
      if (editing.value && editingAnnotation.value) {
        setTimeout(() => {
          editAnnotationLayer.changeData(editingAnnotation.value);
        }, 100);
      }
    };
    watch(props.annotations, () => {
      localAnnotations.value = props.annotations;
    });
    watch(() => props.selectedId, () => {
        selectedAnnotationId.value = props.selectedId;
        triggerUpdate();
    });
    onMounted(() => {
      if (props.spectroInfo) {
        rectAnnotationLayer = new RectangleLayer(props.geoViewerRef, event, props.spectroInfo);
        editAnnotationLayer = new EditAnnotationLayer(props.geoViewerRef, event, props.spectroInfo);
        rectAnnotationLayer.formatData(localAnnotations.value, selectedAnnotationId.value);
        rectAnnotationLayer.redraw();
      }
    });

    return {};
  },
});
</script>

<template>
  <div />
</template>
