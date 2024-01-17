<script lang="ts">
import { computed, defineComponent, PropType, ref, Ref, watch } from "vue";
import { SpectroInfo } from './geoJS/geoJSUtils';
import { deleteAnnotation, patchAnnotation, Species, SpectrogramAnnotation } from "../api/api";

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
    },
    recordingId: {
        type: String,
        required: true,
    }
  },
  emits: ['update:annotation', 'delete:annotation'],
  setup(props, { emit }) {
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
    const updateAnnotation = async () => {
        if (props.annotation) {
            // convert species names to Ids;
            const speciesIds: number[] = [];
            speciesEdit.value.forEach((item) => {
                const found = props.species.find((specie) => specie.common_name === item);
                if (found) {
                    speciesIds.push(found.id);
                }
            });
            await patchAnnotation(props.recordingId, props.annotation?.id, { ...props.annotation, comments: comments.value }, speciesIds );
            // Signal to redownload the updated annotation values if possible
            emit('update:annotation');
        }

    };

    const deleteAnno = async () => {
        if (props.annotation && props.recordingId) {
            await deleteAnnotation(props.recordingId, props.annotation.id);
            emit('delete:annotation');
        }
    };
    return {
        speciesList,
        speciesEdit,
        comments,
        updateAnnotation,
        deleteAnno
    };
  },
});
</script>

<template>
  <v-card>
    <v-card-title>
      <v-row class="pa-2">
        Edit Annotations
        <v-spacer />
        <v-btn
          size="x-small"
          color="error"
          class="mt-1"
          @click="deleteAnno()"
        >
          Delete<v-icon>mdi-delete</v-icon>
        </v-btn>
      </v-row>
    </v-card-title>
    <v-row>
      <v-select
        v-model="speciesEdit"
        multiple
        closable-chips
        chips
        :items="speciesList"
        label="Species"
        @update:model-value="updateAnnotation()"
      />
    </v-row>
    <v-row>
      <v-textarea
        v-model="comments"
        label="Comments"
        @change="updateAnnotation()"
      />
    </v-row>
  </v-card>
</template>

<style lang="scss" scoped>

</style>
