import { ref, Ref } from 'vue';
import { cloneDeep } from 'lodash';

const annotationState: Ref<AnnotationState> = ref('');
type LayersVis = 'time' | 'freq' | 'species' |'grid';
const layerVisibility: Ref<LayersVis[]> = ref([]);

type AnnotationState = '' | 'editing' | 'creating';
export default function useState() {
    const setAnnotationState = (state: AnnotationState) => {
        annotationState.value = state;
    };
    function toggleLayerVisibility(value: LayersVis) {
        const index = layerVisibility.value.indexOf(value);
        const clone = cloneDeep(layerVisibility.value);
        if (index === -1) {
          // If the value is not present, add it
          clone.push(value);
        } else {
          // If the value is present, remove it
          clone.splice(index, 1);
        }      
        layerVisibility.value = clone;
      }
          return {
        annotationState,
        setAnnotationState,
        toggleLayerVisibility,
        layerVisibility,
    };
}

