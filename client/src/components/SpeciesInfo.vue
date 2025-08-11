<script lang="ts">
import { computed, defineComponent, PropType, ref } from "vue";
import { Species } from "../api/api";
import { cloneDeep } from "lodash";

export default defineComponent({
  name: "SpeciesInfo",
  components: {},
  props: {
    speciesList: {
      type: Array as PropType<Species[]>,
      required: true,
    },
    selectedSpecies: {
      type: Array as PropType<string[]>,
      default: () => [],
    },
  },
  emits: ['dismiss'],
  setup(props) {
    const itemsPerPage = ref(-1);
    const displayDialog = ref(false);
    const headers = ref([
      {
        title: "Species Code",
        key: "species_code",
      },
      {
        title: "Category",
        key: "category",
      },
      {
        title: "Species",
        key: "species",
      },
      {
        title: "Common Name",
        key: "common_name",
      },
    ]);

    const categoryPriority: Record<string, number> = {
      individual: 0,
      couplet: 1,
      frequency: 2,
      noid: 3,
    };
    const categoryColors: Record<string, string> = {
      individual: 'primary',
      couplet: 'secondary',
      frequency: 'warning',
      noid: '',
    };

    const orderedSpecies = computed(() => {
      const copiedSpecies = cloneDeep(props.speciesList);
      copiedSpecies.sort((a, b) => {
        const aSelected = props.selectedSpecies.includes(a.species_code);
        const bSelected = props.selectedSpecies.includes(b.species_code);

        // 1. Selected species come first
        if (aSelected && !bSelected) return -1;
        if (!aSelected && bSelected) return 1;

        // 2. Then by category priority
        const aCat = categoryPriority[a.category] ?? 999;
        const bCat = categoryPriority[b.category] ?? 999;
        if (aCat !== bCat) return aCat - bCat;

        // 3. Finally by species_code
        return a.species_code.localeCompare(b.species_code);
      });
      return copiedSpecies;
    });

    return {
      headers,
      orderedSpecies,
      itemsPerPage,
      displayDialog,
      categoryColors,
    };
  },
});
</script>

<template>
  <span>
    <v-btn size="x-small" color="primary" class="ml-3" @click="displayDialog = true"> Species Codes </v-btn>
    <v-dialog v-model="displayDialog" width="800">
      <v-card>
        <v-card-title class="d-flex flex-column">
          <v-row class="align-center">
            <h2 class="mr-4">Species Codes</h2>
            <v-spacer />
            <v-icon size="large" @click="displayDialog = false">mdi-close</v-icon>
          </v-row>
          <v-row class="mt-2">
            <v-chip color="#0000FF" class="ma-1" label
              small>
              Highlighted = Selected Species
            </v-chip>
          </v-row>
        </v-card-title>
        <v-card-text>
          <v-data-table v-model:items-per-page="itemsPerPage" :headers="headers" :items="orderedSpecies"
            hide-default-footer density="compact" class="elevation-1 my-recordings">
            <template #item="{ item }">
              <tr :class="selectedSpecies.includes(item.species_code) ? 'selected-row' : ''">
                <td>{{ item.species_code }}</td>
                <td>
                  <span :class="categoryColors[item.category] ? `text-${categoryColors[item.category]}` : ''">
                    {{ item.category.charAt(0).toUpperCase() + item.category.slice(1) }}
                  </span>
                </td>
                <td>{{ item.species }}</td>

                <td>{{ item.common_name }}</td>
              </tr>
            </template>

          </v-data-table>
        </v-card-text>
        <v-card-actions>
          <v-row>
            <v-spacer />
            <v-btn color="primary" variant="outlined" @click="displayDialog = false">
              Ok
            </v-btn>
            <v-spacer />
          </v-row>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </span>
</template>

<style scoped>
.selected-row {
  background-color: rgba(0, 0, 255, 0.05);
  /* Light blue tint */
}

.text-primary {
  color: #1976d2;
  /* Vuetify primary color (adjust if needed) */
}

.text-secondary {
  color: #9c27b0;
}

.text-warning {
  color: #fb8c00;
}
</style>