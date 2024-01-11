<script lang="ts">
import { defineComponent, onMounted, PropType, Ref, ref } from 'vue';
import { SpectrogramAnnotation } from '../../api/api';
import { SpectroInfo } from './geoJSUtils';
import RectangleLayer from './layers/rectangleLayer';

export default defineComponent({
    name:'LayerManager',
    props: {
        geoViewerRef: {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            type: Object as PropType<any>,
            required: true,
        },
        spectroInfo: {
            type: Object as PropType<SpectroInfo | undefined>,
            default: () => undefined
        },
        annotations: {
            type: Array as PropType<SpectrogramAnnotation[]>,
            default: () => [],
        }
    },
    setup(props) {
        const selectedAnnotationId: Ref<null | number> = ref(null);
        const hoveredAnnotationId: Ref<null | number> = ref(null);
        const editing = ref(false);
        let rectAnnotationLayer: RectangleLayer;
        // eslint-disable-next-line @typescript-eslint/no-unused-vars, @typescript-eslint/no-explicit-any
        const event = (type: string, data: any) => {
            // Will handle clicking, selecting and editing here
            if (type === 'annotation-clicked') {
                selectedAnnotationId.value = data.id;
                editing.value = data.edit;
            }
            if (type === 'annotation-hover') {
                hoveredAnnotationId.value = data.id;
            }
            if (type === 'annotation-right-clicked') {
                hoveredAnnotationId.value = data.id;
                editing.value = data.edit;
            }
            triggerUpdate();
        };
        const triggerUpdate = () => {
            if (rectAnnotationLayer) {
                rectAnnotationLayer.formatData(props.annotations, selectedAnnotationId.value);
                rectAnnotationLayer.redraw();
            }
        };
        onMounted(() => {
            if (props.spectroInfo) {
                rectAnnotationLayer = new RectangleLayer(props.geoViewerRef, event, props.spectroInfo);
                rectAnnotationLayer.formatData(props.annotations, selectedAnnotationId.value);
                rectAnnotationLayer.redraw();
            }
        });

        return {
            
        };
    }
});
</script>

<template>
  <div />
</template>