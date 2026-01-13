<script setup lang="ts">
import { ref, watch } from 'vue';
import { createOrUpdateVettingDetailsForUser } from '@api/api';
import useState from '@use/useState';

const { currentUserId, reviewerMaterials } = useState();

const referenceDialog = ref(false);
const reviewerMaterialsDisplay = ref('');
const valid = ref(true);
const error = ref('');

async function saveReviewerMaterials() {
  if (!currentUserId.value || !valid.value) return;
  try {
    const details = await createOrUpdateVettingDetailsForUser(currentUserId.value, reviewerMaterialsDisplay.value);
    reviewerMaterials.value = details.reference_materials;
  } catch(err) {
    error.value = 'There was a problem saving your changes. Please try again';
  }
}

watch(reviewerMaterials, () => reviewerMaterialsDisplay.value = reviewerMaterials.value);

</script>

<template>
  <v-dialog
    v-model="referenceDialog"
    max-width="50%"
  >
    <template #activator="{ props }">
      <v-btn
        v-bind="props"
      >
        Add reference materials
      </v-btn>
    </template>
    <v-card>
      <v-card-title>
        Reference Materials
      </v-card-title>
      <v-card-text>
        <v-form
          v-model="valid"
        >
          <v-textarea
            v-model="reviewerMaterialsDisplay"
            placeholder="Describe any reference materials used during labeling"
            :rules="[
              v => v.length <= 2000 || 'Only 2000 characters are allowed'
            ]"
            counter="2000"
          />
          <span
            v-if="error"
          >
            <v-icon color="error">mdi-alert-circle-outline</v-icon>
            {{ error }}
          </span>
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-btn
          @click="referenceDialog = false"
        >
          Close
        </v-btn>
        <v-btn
          color="primary"
          :disabled="!valid"
          @click="saveReviewerMaterials"
        >
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
