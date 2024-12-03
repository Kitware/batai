<script lang="ts">
import { computed, defineComponent, PropType, ref, Ref, watch } from "vue";
import { SpectroInfo } from './geoJS/geoJSUtils';
import { deleteAnnotation, deleteFileAnnotation, deleteTemporalAnnotation, FileAnnotation, patchAnnotation, patchTemporalAnnotation, Species, SpectrogramAnnotation, SpectrogramTemporalAnnotation } from "../api/api";
import useState from "../use/useState";
import SpeciesInfo from "./SpeciesInfo.vue";
export default defineComponent({
  name: "AnnotationEditor",
  components: {
    SpeciesInfo,
  },
  props: {
    spectroInfo: {
      type: Object as PropType<SpectroInfo | undefined>,
      default: () => undefined,
    },
    annotation: {
      type: Object as PropType<FileAnnotation | null>,
      default: () => null,
    },
    species: {
        type: Array as PropType<Species[]>,
        required: true,
    },
    recordingId: {
        type: Number,
        required: true,
    }
  },
  emits: ['update:annotation', 'delete:annotation'],
  setup(props, { emit }) {
    const speciesList = computed(() => {
        return props.species.map((item) => (item.species_code || item.common_name)).sort();
    });

    const speciesEdit: Ref<string[]> = ref( props.annotation?.species?.map((item) => item.species_code || item.common_name) || []);
    const comments: Ref<string> = ref(props.annotation?.comments || '');
    const confidence: Ref<number> = ref(1.0);

    watch(() => props.annotation, () => {
        if (props.annotation?.species) {
            speciesEdit.value = props.annotation.species.map((item) => item.species_code || item.common_name);
        }
        if (props.annotation?.comments) {
            comments.value = props.annotation.comments;
        }
        if (props.annotation) {
            confidence.value = props.annotation.confidence;
        }
    });
    const updateAnnotation = async () => {
        if (props.annotation) {
            // convert species names to Ids;
            const speciesIds: number[] = [];
            speciesEdit.value.forEach((item) => {
                const found = props.species.find((specie) => specie.species_code === item);
                if (found) {
                    speciesIds.push(found.id);
                }
            });
            const updateType = type.value.join('+');
            if (selectedType.value === 'pulse') {
              await patchAnnotation(props.recordingId, props.annotation?.id, { ...props.annotation, comments: comments.value, confidence: confidence.value }, speciesIds );
            } else if (selectedType.value === 'sequence') {
              await patchTemporalAnnotation(props.recordingId, props.annotation.id, {...props.annotation, comments: comments.value, type: updateType }, speciesIds);
            }
            // Signal to redownload the updated annotation values if possible
            emit('update:annotation');
        }

    };

    const deleteAnno = async () => {
      if (props.annotation && props.recordingId) {
            await deleteFileAnnotation(props.annotation.id,);
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
    <v-card-text>
      <v-row>
        <SpeciesInfo
          :species-list="species"
          :selected-species="speciesEdit"
          class="my-2"
        />
      </v-row>
      <v-row>
        <v-autocomplete
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
    </v-card-text> 
  </v-card>
</template>

<style lang="scss" scoped>

</style>
