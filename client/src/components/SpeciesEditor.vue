<script lang="ts">
import { defineComponent, PropType, ref, watch } from "vue";
import { Species } from "@api/api";
import SingleSpecieEditor from "./SingleSpecieEditor.vue";

export default defineComponent({
  name: "SpeciesEditor",
  components: { SingleSpecieEditor },
  props: {
    modelValue: {
      type: Array as PropType<string[]>,
      default: () => [],
    },
    speciesList: {
      type: Array as PropType<Species[]>,
      default: () => [],
    },
    disabled: {
      type: Boolean,
      default: false,
    },
    multiple: {
      type: Boolean,
      default: false,
    },
  },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    // Internal: one slot per row, at least one. Empty string = no selection in that slot.
    const localSpeciesList = ref<string[]>(
      props.modelValue?.length ? [...props.modelValue] : [""]
    );
    const addSpeciesConfirmOpen = ref(false);

    watch(
      () => props.modelValue,
      (newVal) => {
        const arr = newVal ?? [];
        localSpeciesList.value = arr.length ? [...arr] : [""];
      },
      { immediate: true }
    );

    function emitValue() {
      const values = localSpeciesList.value.filter((s) => s != null && s !== "");
      emit("update:modelValue", values);
    }

    function onSlotUpdate(index: number, value: string | null) {
      const code = value ?? "";
      if (localSpeciesList.value[index] !== code) {
        localSpeciesList.value[index] = code;
        emitValue();
      }
    }

    function openAddSpeciesConfirm() {
      addSpeciesConfirmOpen.value = true;
    }

    function closeAddSpeciesConfirm() {
      addSpeciesConfirmOpen.value = false;
    }

    function confirmAddSpecies() {
      localSpeciesList.value.push("");
      closeAddSpeciesConfirm();
      // Don't emit: the new slot is empty so the selected list is unchanged.
      // Emit will happen when the user picks a species in the new row.
    }

    function removeSpecies(index: number) {
      if (localSpeciesList.value.length <= 1) return;
      localSpeciesList.value.splice(index, 1);
      emitValue();
    }

    return {
      localSpeciesList,
      onSlotUpdate,
      openAddSpeciesConfirm,
      closeAddSpeciesConfirm,
      confirmAddSpecies,
      addSpeciesConfirmOpen,
      removeSpecies,
    };
  },
});
</script>

<template>
  <div class="species-editor">
    <div
      v-for="(slot, index) in localSpeciesList"
      :key="index"
      class="species-editor-row mb-2 mt-3"
    >
      <SingleSpecieEditor
        :model-value="slot || null"
        :species-list="speciesList"
        :disabled="disabled"
        :show-delete="localSpeciesList.length > 1"
        @update:model-value="onSlotUpdate(index, $event)"
        @delete="removeSpecies(index)"
      />
    </div>
    <v-btn
      size="small"
      variant="outlined"
      color="primary"
      :disabled="disabled"
      class="mt-1 mb-2"
      v-tooltip="'Add another species'"
      @click="openAddSpeciesConfirm"
    >
      <v-icon start>mdi-plus</v-icon>
      Add Bat
    </v-btn>
    <v-dialog
      v-model="addSpeciesConfirmOpen"
      max-width="400"
      persistent
    >
      <v-card>
        <v-card-title>Add another Bat?</v-card-title>
        <v-card-text>
          This is intended only when multiple bats are found in the same recording. Do you want to add a new bat?
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="closeAddSpeciesConfirm"
          >
            Cancel
          </v-btn>
          <v-btn
            variant="flat"
            color="primary"
            @click="confirmAddSpecies"
          >
            Add species
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped>
.species-editor {
  width: 100%;
}
.species-editor-row {
  min-width: 0;
  width: 100%;
}
</style>
