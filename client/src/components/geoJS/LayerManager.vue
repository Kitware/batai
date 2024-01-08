<script lang="ts">
import { defineComponent, PropType } from 'vue';
import { SpectroInfo } from './geoJSUtils';
import RectangleLayer from './layers/rectangleLayer';

export default defineComponent({
    name:'LayerManager',
    props: {
        geoJSRef: {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            type: Object as PropType<any>,
            required: true,
        },
        spectroInfo: {
            type: Object as PropType<SpectroInfo>,
            required: true,
        }
    },
    setup(props) {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const event = (type: string, data: any) => {
            // Will handle clicking, selecting and editing here
            //console.log(type);
            //console.log(data);
        };
        const rectAnnotationLayer = new RectangleLayer(props.geoJSRef, event, props.spectroInfo);

        return {
            
        };
    }
});
</script>

<template>
  <div />
</template>