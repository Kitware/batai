<script lang="ts">
import { defineComponent, PropType, ref, computed } from 'vue';
import { FileAnnotation, Species, UpdateFileAnnotation } from '@api/api';
import { pushNABatFileAnnotationToNABat } from '../api/NABatApi';

export default defineComponent({
  name: 'SpeciesNABatSave',
  props: {
    selectedSpecies: {
      type: Array as PropType<string[]>,
      required: true,
    },
    speciesList: {
      type: Array as PropType<Species[]>,
      required: true,
    },
    annotation: {
      type: Object as PropType<FileAnnotation | null>,
      default: () => null,
    },
    recordingId: {
      type: Number,
      required: true,
    },
    apiToken: {
      type: String,
      default: () => '',
    },
  },
  emits: ['close'],

  setup(props, { emit }) {
    const dialog = ref(false);
    const selected = ref<number | null>(null);
    const submitting = ref(false);
    const error = ref<string | null>(null);

    const filteredSpecies = computed(() =>
      props.speciesList.filter(s => props.selectedSpecies.includes(s.species_code))
    );

    const categoryColors: Record<string, string> = {
      'single': 'primary',
      'multiple': 'secondary',
      'frequency': 'warning',
      'noid': '',
    };

    const saveSelection = async () => {
      if (selected.value && props.annotation) {
        submitting.value = true;
        error.value = null;

        try {
          const updateAnnotation: UpdateFileAnnotation & { apiToken?: string } = {
            recordingId: props.recordingId,
            confidence: 1.0,
            comments: '',
            model: 'User Defined',
            species: [selected.value],
            id: props.annotation.id,
            apiToken: props.apiToken,
          };

          await pushNABatFileAnnotationToNABat(props.annotation.id, updateAnnotation);
          dialog.value = false;
          emit('close');
        } catch (e) {
          error.value = 'Failed to update selection.';
          console.error(e);
        } finally {
          submitting.value = false;
        }
      } else {
        error.value = 'Please select a species.';
      }
    };

    return {
      dialog,
      filteredSpecies,
      selected,
      submitting,
      error,
      saveSelection,
      categoryColors,
    };
  },
});
</script>
<template>
  <span>
    <v-btn
      size="small"
      color="success"
      :disabled="!selectedSpecies.length || submitting"
      @click="dialog = true"
    >
      Save NABat Label
    </v-btn>

    <v-dialog
      v-model="dialog"
      max-width="600"
    >
      <v-card>
        <v-card-title>
          <v-row class="my-2 align-center">
            <h3 class="mr-2">Save NABat Label</h3>
            <v-spacer />
            <v-icon
              size="large"
              class="cursor-pointer"
              @click="dialog = false"
            >mdi-close</v-icon>
          </v-row>
        </v-card-title>

        <v-card-text>
          <p>Please select one of your species to push to the NABat database. The NABat database currently only supports
            a single label.</p>

          <v-alert
            v-if="error"
            type="error"
            dense
            class="mb-2"
          >
            {{ error }}
          </v-alert>

          <v-radio-group
            v-model="selected"
            :disabled="submitting"
            hide-details
          >
            <v-radio
              v-for="species in filteredSpecies"
              :key="species.species_code"
              :value="species.id"
              style="border: 1px solid black"
            >
              <template #label>
                <div
                  :class="['species-label', categoryColors[species.category] && `text-${categoryColors[species.category]}`]"
                >
                  <strong>{{ species.common_name }}</strong><br>
                  <small>
                    Code: {{ species.species_code }} |
                    Scientific: {{ species.family }} |
                    Category: {{ species.category }}
                  </small>
                </div>
              </template>
            </v-radio>
          </v-radio-group>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn
            text
            color="error"
            variant="flat"
            :disabled="submitting"
            @click="dialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="success"
            variant="flat"
            :disabled="!selected || submitting"
            @click="saveSelection"
          >
            Save
          </v-btn>
          <v-progress-circular
            v-if="submitting"
            indeterminate
            color="primary"
            size="20"
          />
        </v-card-actions>
      </v-card>
    </v-dialog>
  </span>
</template>
