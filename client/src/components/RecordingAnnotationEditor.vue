<script lang="ts">
import { computed, defineComponent, PropType, ref, Ref, watch } from "vue";
import { SpectroInfo } from './geoJS/geoJSUtils';
import { deleteFileAnnotation, FileAnnotation, patchFileAnnotation, Species, UpdateFileAnnotation } from "../api/api";
import { deleteNABatFileAnnotation, patchNABatFileAnnotationLocal } from "../api/NABatApi";
import SpeciesInfo from "./SpeciesInfo.vue";
import SpeciesEditor from "./SpeciesEditor.vue";
import SpeciesNABatSave from "./SpeciesNABatSave.vue";
export default defineComponent({
  name: "AnnotationEditor",
  components: {
    SpeciesInfo,
    SpeciesEditor,
    SpeciesNABatSave,
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
    },
    apiToken: {
      type: String,
      default: () => '',
    },
    type: {
      type: String as PropType<'nabat' | null>,
      default: () => null,
    },
  },
  emits: ['update:annotation', 'delete:annotation'],
  setup(props, { emit }) {

    const speciesEdit: Ref<string[]> = ref( props.annotation?.species?.map((item) => item.species_code || item.common_name) || []);
    const comments: Ref<string> = ref(props.annotation?.comments || '');
    const confidence: Ref<number> = ref(props.annotation?.confidence || 1.0);
    const singleSpecies: Ref<string | null> = ref(props.annotation?.species.length ? props.annotation.species[0].species_code : null);
    watch(() => props.annotation, () => {
        if (props.annotation?.species) {
            speciesEdit.value = props.annotation.species.map((item) => item.species_code || item.common_name);
        }
        if (props.annotation) {
            comments.value = props.annotation.comments || '';
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

            const updateAnnotation: UpdateFileAnnotation & { apiToken?: string } = {
              recordingId: props.recordingId,
              comments: comments.value,
              confidence: confidence.value,
              model: 'User Defined',
              species: speciesIds,
              id: props.annotation.id,
              apiToken: props.apiToken,
            };
            props.type === 'nabat' ? await patchNABatFileAnnotationLocal(props.annotation.id, updateAnnotation) : await patchFileAnnotation(props.annotation.id, updateAnnotation);
            // Signal to redownload the updated annotation values if possible
            emit('update:annotation');
        }

    };

    

    const deleteAnnotation = async () => {
      if (props.annotation && props.recordingId) {
            props.type === 'nabat' ? await deleteNABatFileAnnotation(props.annotation.id, props.apiToken, props.recordingId) : await deleteFileAnnotation(props.annotation.id,);
            emit('delete:annotation');
        }
    };
    return {
        speciesEdit,
        confidence,
        comments,
        updateAnnotation,
        deleteAnnotation,
        singleSpecies,
    };
  },
});
</script>

<template>
  <v-card>
    <v-card-title>
      <v-row class="pa-2">
        Choose Labels
        <v-spacer />
        <v-btn
          v-if="type !== 'nabat'"
          size="x-small"
          color="error"
          class="mt-1"
          @click="deleteAnnotation()"
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
        <SpeciesEditor
          :key="`species_${annotation?.id}`"
          v-model="speciesEdit"
          :species-list="species"
          @update:model-value="updateAnnotation()"
        />
      </v-row>
      <v-row v-if="type === 'nabat'">
        <SpeciesNABatSave
          :selected-species="speciesEdit"
          :species-list="species"
          :recording-id="recordingId"
          :annotation="annotation"
          :api-token="apiToken"
        />
      </v-row>
      <v-row
        v-if="type !== 'nabat'"
      >
        <v-slider
          v-model="confidence"
          min="0"
          max="1"
          step="0.01"
          :label="`Confidence (${confidence.toFixed(2)})`"
          @end="updateAnnotation()"
        />
      </v-row>
      <v-row
        v-if="type !== 'nabat'"
      >
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
