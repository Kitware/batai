<script lang="ts">
import { computed, defineComponent, PropType, ref, Ref, watch } from "vue";
import { SpectroInfo } from './geoJS/geoJSUtils';
import {
  deleteFileAnnotation,
  FileAnnotation,
  patchFileAnnotation,
  Species,
  UpdateFileAnnotation,
  submitFileAnnotation,
} from "../api/api";
import { deleteNABatFileAnnotation, patchNABatFileAnnotationLocal } from "../api/NABatApi";
import useState from "@use/useState";
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
    submittedAnnotationId: {
      type: Number as PropType<number | undefined>,
      default: () => undefined,
    },
  },
  emits: ['update:annotation', 'delete:annotation'],
  setup(props, { emit }) {
    const { configuration, currentUser } = useState();
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

    const submitAnnotation = async () => {
      if (props.annotation && props.recordingId) {
        await submitFileAnnotation(props.annotation.id);
        emit('update:annotation');
      }
    };

    const canSubmit = computed(() => (
      props.annotation
      && props.annotation.owner === currentUser.value
      && props.annotation.model === 'User Defined'
      && configuration.value.mark_annotations_completed_enabled
    ));

    const submissionTooltip = computed(() => {
      if (props.submittedAnnotationId !== undefined && props.submittedAnnotationId !== props.annotation?.id) {
        return 'You have already submitted a different annotation for this recording.';
      }
      if (props.annotation && props.annotation.submitted) {
        return 'This annotation has been submitted. This cannot be undone.';
      }
      return 'Submit this annotation. This action cannot be undone.';
    });

    return {
        speciesEdit,
        confidence,
        comments,
        updateAnnotation,
        deleteAnnotation,
        submitAnnotation,
        singleSpecies,
        configuration,
        canSubmit,
        submissionTooltip,
    };
  },
});
</script>

<template>
  <v-card>
    <v-card-title>
      <v-row class="pa-2">
        Choose Label
        <v-tooltip
          v-if="type === 'nabat'"
          width="250"
          right
        >
          <template #activator="{ props }">
            <v-icon
              v-bind="props"
              size="x-small"
            >
              mdi-information
            </v-icon>
          </template>
          <span>
            Each user may only add one label per file. Once you have saved
            your selection it may not be deleted.
          </span>
        </v-tooltip>
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
          :disabled="annotation?.submitted"
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
        v-if="type !== 'nabat' && !configuration.mark_annotations_completed_enabled"
      >
        <v-textarea
          v-model="comments"
          label="Comments"
          @change="updateAnnotation()"
        />
      </v-row>
      <v-row v-if="canSubmit">
        <v-tooltip>
          <template #activator="{ props }">
            <div
              v-bind="props"
            >
              <v-btn
                flat
                color="primary"
                :disabled="annotation.submitted || (submittedAnnotationId !== undefined && annotation.id !== submittedAnnotationId)"
                @click="submitAnnotation"
              >
                Submit
                <template #append>
                  <v-icon>mdi-check</v-icon>
                </template>
              </v-btn>
            </div>
          </template>
          {{ submissionTooltip }}
        </v-tooltip>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<style lang="scss" scoped>

</style>
