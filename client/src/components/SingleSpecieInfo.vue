<script lang="ts">
import { computed, defineComponent, PropType, ref, watch } from "vue";
import { Species } from "../api/api";
import { cloneDeep } from "lodash";

export default defineComponent({
  name: "SingleSpecieInfo",
  props: {
    modelValue: {
      type: String as PropType<string | null>,
      default: null,
    },
    speciesList: {
      type: Array as PropType<Species[]>,
      required: true,
    },
    disabled: {
      type: Boolean,
      default: false,
    },
  },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    const itemsPerPage = ref(-1);
    const displayDialog = ref(false);
    const pendingSelection = ref<string | null>(null);
    const searchQuery = ref("");

    const headers = ref([
      { title: "", key: "selected", sortable: true, width: "48px" },
      { title: "Species Code", key: "species_code" },
      { title: "Category", key: "category" },
      { title: "Species", key: "species" },
      { title: "Common Name", key: "common_name" },
    ]);

    const categoryPriority: Record<string, number> = {
      single: 0,
      multiple: 1,
      frequency: 2,
      noid: 3,
    };
    const categoryColors: Record<string, string> = {
      single: "primary",
      multiple: "secondary",
      frequency: "warning",
      noid: "",
    };

    const orderedSpecies = ref<Species[]>([]);

    function sortSpecies(species: Species[], selectedCode: string | null) {
      const copied = cloneDeep(species);
      copied.sort((a, b) => {
        const aSelected = selectedCode === a.species_code;
        const bSelected = selectedCode === b.species_code;
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
        pendingSelection.value = props.modelValue ?? null;
        orderedSpecies.value = sortSpecies(props.speciesList, props.modelValue ?? null);
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
        selected: pendingSelection.value === s.species_code,
      }));
    });

    const hasChanges = computed(
      () => (pendingSelection.value ?? null) !== (props.modelValue ?? null)
    );

    const toggleSpecies = (speciesCode: string) => {
      if (props.disabled) return;
      pendingSelection.value =
        pendingSelection.value === speciesCode ? null : speciesCode;
    };

    const closeDialog = () => {
      displayDialog.value = false;
    };

    const saveAndClose = () => {
      emit("update:modelValue", pendingSelection.value);
      displayDialog.value = false;
    };

    const buttonLabel = computed(() =>
      props.modelValue ? props.modelValue : "Species Code"
    );

    const selectedSpecies = computed(() =>
      props.modelValue
        ? props.speciesList.find((s) => s.species_code === props.modelValue) ?? null
        : null
    );

    return {
      headers,
      orderedSpecies,
      filteredSpecies,
      itemsPerPage,
      displayDialog,
      categoryColors,
      searchQuery,
      toggleSpecies,
      hasChanges,
      closeDialog,
      saveAndClose,
      buttonLabel,
      selectedSpecies,
    };
  },
});
</script>

<template>
  <span>
    <v-menu
      location="bottom"
      open-on-hover
      :close-on-content-click="false"
      transition="scale-transition"
    >
      <template #activator="{ props: menuProps }">
        <v-btn
          v-bind="menuProps"
          size="x-small"
          color="primary"
          class="mr-2 flex-shrink-0"
          :disabled="disabled"
          @click="displayDialog = true"
        >
          {{ buttonLabel }}
        </v-btn>
      </template>
      <v-card max-width="320" class="pa-3">
        <template v-if="selectedSpecies">
          <div class="text-subtitle-2 mb-2">Selected species</div>
          <div class="text-body-2">
            <div><strong>Code:</strong> {{ selectedSpecies.species_code }}</div>
            <div><strong>Common name:</strong> {{ selectedSpecies.common_name }}</div>
            <div v-if="selectedSpecies.species">
              <strong>Species:</strong> {{ selectedSpecies.species }}
            </div>
            <div>
              <strong>Category:</strong>
              {{ selectedSpecies.category.charAt(0).toUpperCase() + selectedSpecies.category.slice(1) }}
            </div>
          </div>
        </template>
        <div class="text-caption text-medium-emphasis mt-2 pt-2" style="border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));">
          Click the button to open the editor for all species.
        </div>
      </v-card>
    </v-menu>
    <v-dialog v-model="displayDialog" width="800" persistent>
      <v-card class="d-flex flex-column">
        <v-card-title class="flex-shrink-0 d-flex flex-column">
          <v-row class="align-center">
            <h2 class="mr-4">Select Species</h2>
            <v-spacer />
            <v-icon size="large" @click="closeDialog">mdi-close</v-icon>
          </v-row>
          <v-row class="mt-2">
            <v-chip color="#0000FF" class="ma-1" label small>
              Highlighted = Selected Species
            </v-chip>
          </v-row>
        </v-card-title>
        <v-card-text
          class="flex-grow-1 overflow-y-auto pa-0"
          style="max-height: 60vh"
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
                  <span
                    :class="
                      categoryColors[item.category]
                        ? `text-${categoryColors[item.category]}`
                        : ''
                    "
                  >
                    {{
                      item.category.charAt(0).toUpperCase() +
                      item.category.slice(1)
                    }}
                  </span>
                </td>
                <td>{{ item.species ?? "" }}</td>
                <td>{{ item.common_name }}</td>
              </tr>
            </template>
          </v-data-table>
        </v-card-text>
        <v-card-actions class="flex-shrink-0">
          <v-spacer />
          <template v-if="hasChanges">
            <v-btn variant="outlined" @click="closeDialog"> Cancel </v-btn>
            <v-btn color="primary" @click="saveAndClose"> Save </v-btn>
          </template>
          <v-btn v-else color="primary" variant="outlined" @click="closeDialog">
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
}

.text-primary {
  color: #1976d2;
}

.text-secondary {
  color: #9c27b0;
}

.text-warning {
  color: #fb8c00;
}
</style>
