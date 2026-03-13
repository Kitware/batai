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
    vettingMode: {
      type: Boolean,
      default: false,
    },
    annotationComment: {
      type: String,
      default: "",
    },

  },
  emits: ["update:modelValue", "deleteBlankAnnotation", "saveComment"],
  setup(props, { emit }) {
    // Internal: one slot per row, at least one. Empty string = no selection in that slot.
    const localSpeciesList = ref<string[]>(
      props.modelValue?.length ? [...props.modelValue] : [""]
    );
    const addSpeciesConfirmOpen = ref(false);
    const commentDialogOpen = ref(false);
    const commentDraft = ref("");

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

    function onSlotDelete(index: number) {
      if (localSpeciesList.value.length <= 1 && (localSpeciesList.value[0] ?? "") === "") {
        emit("deleteBlankAnnotation");
      } else {
        removeSpecies(index);
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

    function openCommentDialog() {
      commentDraft.value = props.annotationComment ?? "";
      commentDialogOpen.value = true;
    }

    function closeCommentDialog() {
      commentDialogOpen.value = false;
    }

    function saveComment() {
      emit("saveComment", commentDraft.value);
      closeCommentDialog();
    }

    function removeComment() {
      commentDraft.value = "";
      emit("saveComment", "");
      closeCommentDialog();
    }

    return {
      localSpeciesList,
      onSlotUpdate,
      onSlotDelete,
      openAddSpeciesConfirm,
      closeAddSpeciesConfirm,
      confirmAddSpecies,
      addSpeciesConfirmOpen,
      removeSpecies,
      commentDialogOpen,
      commentDraft,
      openCommentDialog,
      closeCommentDialog,
      saveComment,
      removeComment,
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
        @delete="onSlotDelete(index)"
      />
    </div>
    <v-row dense class="mt-1 mb-2">
      <v-col>
      <v-btn
        v-tooltip="'Add another bat'"
        size="small"
        variant="outlined"
        color="primary"
        :disabled="disabled"
        @click="openAddSpeciesConfirm"
      >
        <v-icon start>mdi-plus</v-icon>
        Add Bat
      </v-btn>
      </v-col>
      <v-spacer />
      <v-col>
      <v-btn
        v-if="vettingMode"
        v-tooltip="annotationComment ? `Edit comment: ${annotationComment}` : 'Add optional comment to this annotation'"
        size="small"
        variant="outlined"
        color="primary"
        :disabled="disabled"
        @click="openCommentDialog"
      >
        <v-icon start>{{ annotationComment ? 'mdi-pencil' : 'mdi-plus' }}</v-icon>
        Comment
      </v-btn>
      </v-col>
    </v-row>
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
    <v-dialog
      v-model="commentDialogOpen"
      max-width="500"
      persistent
    >
      <v-card>
        <v-card-title>Comment</v-card-title>
        <v-card-text>
          <p class="text-medium-emphasis mb-3">
            This is an optional comment field that can be attached to the annotation.
          </p>
          <v-textarea
            v-model="commentDraft"
            label="Comment"
            rows="4"
            variant="outlined"
            auto-grow
          />
        </v-card-text>
        <v-card-actions>
          <v-btn
            v-if="commentDraft || annotationComment"
            variant="text"
            color="error"
            @click="removeComment"
          >
            Remove comment
          </v-btn>
          <v-spacer />
          <v-btn
            variant="text"
            @click="closeCommentDialog"
          >
            Cancel
          </v-btn>
          <v-btn
            variant="flat"
            color="primary"
            @click="saveComment"
          >
            Save
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
