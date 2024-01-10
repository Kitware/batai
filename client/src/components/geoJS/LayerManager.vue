<script lang="ts">
import { defineComponent, onMounted, PropType } from 'vue';
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
        // eslint-disable-next-line @typescript-eslint/no-unused-vars, @typescript-eslint/no-explicit-any
        const event = (type: string, data: any) => {
            // Will handle clicking, selecting and editing here
        };
        onMounted(() => {
            if (props.spectroInfo) {
                const rectAnnotationLayer = new RectangleLayer(props.geoViewerRef, event, props.spectroInfo);
                rectAnnotationLayer.formatData(props.annotations);
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