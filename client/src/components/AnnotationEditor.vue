<script lang="ts">
import { computed, defineComponent, PropType, ref, Ref, watch } from "vue";
import { SpectroInfo, useGeoJS } from './geoJS/geoJSUtils';
import { Species, SpectrogramAnnotation } from "../api/api";

export default defineComponent({
  name: "AnnotationEditor",
  components: {
  },
  props: {
    spectroInfo: {
      type: Object as PropType<SpectroInfo | undefined>,
      default: () => undefined,
    },
    annotation: {
      type: Object as PropType<SpectrogramAnnotation | null>,
      default: () => null,
    },
    species: {
        type: Array as PropType<Species[]>,
        required: true,
    }
  },
  setup(props) {
    const speciesList = computed(() => {
        return props.species.map((item) => (item.common_name));
    });
    const speciesEdit: Ref<string[]> = ref( props.annotation?.species?.map((item) => item.common_name) || []);
    const comments: Ref<string> = ref(props.annotation?.comments || '');
    watch(() => props.annotation, () => {
        if (props.annotation?.species) {
            speciesEdit.value = props.annotation.species.map((item) => item.common_name);
        }
        if (props.annotation?.comments) {
            comments.value = props.annotation.comments;
        }
    });
    return {
        speciesList,
        speciesEdit,
        comments,
    };
  },
});
</script>

<template>
  <v-card>
    <v-card-text>Edit Annotation</v-card-text>
    <v-row>
      <v-select
        multiple
        v-model="speciesEdit"
        chips
        :items="speciesList"
        label="Species"
      />
    </v-row>
    <v-row>
      <v-textarea
        v-model="comments"
        label="Comments"
      />
    </v-row>
  </v-card>
</template>

<style lang="scss" scoped>

</style>
