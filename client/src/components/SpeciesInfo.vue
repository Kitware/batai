<script lang="ts">
import { computed, defineComponent, PropType, ref, watch } from "vue";
import { Species } from "../api/api";
import { cloneDeep } from "lodash";

function arraysEqual(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;
  const sortedA = [...a].sort();
  const sortedB = [...b].sort();
  return sortedA.every((v, i) => v === sortedB[i]);
}

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
    disabled: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['dismiss', 'update:selectedSpecies'],
  setup(props, { emit }) {
    const itemsPerPage = ref(-1);
    const displayDialog = ref(false);
    const pendingSelection = ref<string[]>([]);
    const searchQuery = ref("");

    const headers = ref([
      {
        title: "",
        key: "selected",
        sortable: true,
        width: "48px",
      },
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

    const orderedSpecies = ref<Species[]>([]);

    function sortSpecies(species: Species[], selectedCodes: string[]) {
      const copied = cloneDeep(species);
      copied.sort((a, b) => {
        const aSelected = selectedCodes.includes(a.species_code);
        const bSelected = selectedCodes.includes(b.species_code);

        if (aSelected && !bSelected) return -1;
        if (!aSelected && bSelected) return 1;

        const aCat = categoryPriority[a.category] ?? 999;
        const bCat = categoryPriority[b.category] ?? 999;
        if (aCat !== bCat) return aCat - bCat;

        return a.species_code.localeCompare(b.species_code);
      });
      return copied;
    }

    watch(displayDialog, (open) => {
      if (open) {
        pendingSelection.value = [...props.selectedSpecies];
        orderedSpecies.value = sortSpecies(props.speciesList, props.selectedSpecies);
      }
    });

    const filteredSpecies = computed(() => {
      const q = searchQuery.value.trim().toLowerCase();
      const list = !q
        ? orderedSpecies.value
        : orderedSpecies.value.filter(
            (s) =>
              (s.species_code ?? "").toLowerCase().includes(q) ||
              (s.species ?? "").toLowerCase().includes(q) ||
              (s.common_name ?? "").toLowerCase().includes(q) ||
              (s.category ?? "").toLowerCase().includes(q)
          );
      return list.map((s) => ({
        ...s,
        selected: pendingSelection.value.includes(s.species_code),
      }));
    });

    const hasChanges = computed(() =>
      !arraysEqual(pendingSelection.value, props.selectedSpecies)
    );

    const isSelected = (speciesCode: string) =>
      pendingSelection.value.includes(speciesCode);

    const toggleSpecies = (speciesCode: string) => {
      if (props.disabled) return;
      const next = pendingSelection.value.includes(speciesCode)
        ? pendingSelection.value.filter((c) => c !== speciesCode)
        : [...pendingSelection.value, speciesCode];
      pendingSelection.value = next;
    };

    const closeDialog = () => {
      displayDialog.value = false;
    };

    const saveAndClose = () => {
      emit("update:selectedSpecies", [...pendingSelection.value]);
      displayDialog.value = false;
    };

    return {
      headers,
      orderedSpecies,
      filteredSpecies,
      itemsPerPage,
      displayDialog,
      categoryColors,
      searchQuery,
      isSelected,
      toggleSpecies,
      hasChanges,
      closeDialog,
      saveAndClose,
    };
  },
});
</script>

<template>
  <span>
    <v-btn
      size="x-small"
      color="primary"
      class="ml-3"
      :disabled="disabled"
      @click="displayDialog = true"
    > Species Codes </v-btn>
    <v-dialog
      v-model="displayDialog"
      width="800"
      persistent
    >
      <v-card class="d-flex flex-column">
        <v-card-title class="flex-shrink-0 d-flex flex-column">
          <v-row class="align-center">
            <h2 class="mr-4">Species Codes</h2>
            <v-spacer />
            <v-icon
              size="large"
              @click="closeDialog"
            >mdi-close</v-icon>
          </v-row>
          <v-row class="mt-2">
            <v-chip
              color="#0000FF"
              class="ma-1"
              label
              small
            >
              Highlighted = Selected Species
            </v-chip>
          </v-row>
        </v-card-title>
        <v-card-text
          class="flex-grow-1 overflow-y-auto pa-0"
          style="max-height: 60vh;"
        >
          <div class="pa-3 pb-0">
            <v-text-field
              v-model="searchQuery"
              label="Search species"
              placeholder="Code, name, category..."
              density="compact"
              hide-details
              clearable
              prepend-inner-icon="mdi-magnify"
            />
          </div>
          <v-data-table
            v-model:items-per-page="itemsPerPage"
            :headers="headers"
            :items="filteredSpecies"
            hide-default-footer
            density="compact"
            class="elevation-1 my-recordings"
          >
            <template #item="{ item }">
              <tr :class="item.selected ? 'selected-row' : ''">
                <td>
                  <v-checkbox
                    :model-value="item.selected"
                    :disabled="disabled"
                    hide-details
                    density="compact"
                    @update:model-value="toggleSpecies(item.species_code)"
                  />
                </td>
                <td>{{ item.species_code }}</td>
                <td>
                  <span :class="categoryColors[item.category] ? `text-${categoryColors[item.category]}` : ''">
                    {{ item.category.charAt(0).toUpperCase() + item.category.slice(1) }}
                  </span>
                </td>
                <td>{{ item.species ?? '' }}</td>
                <td>{{ item.common_name }}</td>
              </tr>
            </template>
          </v-data-table>
        </v-card-text>
        <v-card-actions class="flex-shrink-0">
          <v-spacer />
          <template v-if="hasChanges">
            <v-btn
              variant="outlined"
              @click="closeDialog"
            >
              Cancel
            </v-btn>
            <v-btn
              color="primary"
              @click="saveAndClose"
            >
              Save
            </v-btn>
          </template>
          <v-btn
            v-else
            color="primary"
            variant="outlined"
            @click="closeDialog"
          >
            OK
          </v-btn>
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