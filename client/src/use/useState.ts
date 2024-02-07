import { ref, Ref } from "vue";
import { cloneDeep } from "lodash";
import * as d3 from "d3";

const annotationState: Ref<AnnotationState> = ref("");
type LayersVis = "time" | "freq" | "species" | "grid" | 'temporal';
const layerVisibility: Ref<LayersVis[]> = ref([]);
const colorScale: Ref<d3.ScaleOrdinal<string, string, never> | undefined> = ref();
const selectedUsers: Ref<string[]> = ref([]);
const currentUser: Ref<string> = ref('');

type AnnotationState = "" | "editing" | "creating" | "disabled";
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
  const setSelectedUsers = (newUsers: string[]) => {
    selectedUsers.value = newUsers;
  };

  function createColorScale(userEmails: string[]) {
    colorScale.value = d3.scaleOrdinal<string>()
    .domain(userEmails)
    .range(d3.schemeCategory10.filter(color => color !== 'red' && color !== 'cyan' && color !== 'yellow'));

  }
    return {
    annotationState,
    setAnnotationState,
    toggleLayerVisibility,
    layerVisibility,
    createColorScale,
    colorScale,
    setSelectedUsers,
    selectedUsers,
    currentUser,
  };
}
