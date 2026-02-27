<script lang="ts">
import {
  defineComponent,
  PropType,
  computed,
  ref,
  watch,
  Ref,
  onMounted,
  onUnmounted,
} from "vue";
import { Species } from "@api/api";
import SingleSpecieInfo from "./SingleSpecieInfo.vue";

export default defineComponent({
  name: "SingleSpecieEditor",
  components: { SingleSpecieInfo },
  props: {
    modelValue: {
      type: String as PropType<string | null>,
      default: null,
    },
    speciesList: {
      type: Array as PropType<Species[]>,
      default: () => [],
    },
    disabled: {
      type: Boolean,
      default: false,
    },
    showDelete: {
      type: Boolean,
      default: false,
    },
  },
  emits: ["update:modelValue", "delete"],
  setup(props, { emit }) {
    const search = ref("");
    const selectedCode = ref<string | null>(props.modelValue);
    const speciesAutocomplete: Ref<HTMLElement | null> = ref(null);

    watch(
      () => props.modelValue,
      (newVal) => {
        selectedCode.value = newVal ?? null;
      },
      { immediate: true }
    );

    watch(selectedCode, (newVal) => {
      emit("update:modelValue", newVal ?? null);
      requestAnimationFrame(() => {
        speciesAutocomplete.value?.blur();
      });
    });

    const categoryColors: Record<string, string> = {
      single: "primary",
      multiple: "secondary",
      frequency: "warning",
      noid: "",
    };

    const groupedItems = computed(() => {
      const groups: Record<string, Species[]> = {};
      for (const s of props.speciesList) {
        const cat =
          s.category.charAt(0).toUpperCase() + s.category.slice(1);
        if (!groups[cat]) groups[cat] = [];
        groups[cat].push(s);
      }
      const result: Array<
        { type: "subheader"; title: string } | (Species & { category: string })
      > = [];
      const groupsOrder = ["Single", "Multiple", "Frequency", "Noid"];
      groupsOrder.forEach((key) => {
        result.push({ type: "subheader", title: key });
        result.push(...(groups[key] ?? []));
      });
      return result;
    });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const customFilter = (filter: string, searchTerm: string, item: any) => {
      if (item.type === "subheader") return false;
      const searchLower = searchTerm.toLocaleLowerCase();
      return (
        item.raw.species_code.toLocaleLowerCase().includes(searchLower) ||
        item.raw.common_name.toLocaleLowerCase().includes(searchLower)
      );
    };

    const speciesShortcut = (e: KeyboardEvent) => {
      if (e.key === "S" && e.shiftKey) {
        e.preventDefault();
        speciesAutocomplete.value?.focus();
      }
    };
    onMounted(() => window.addEventListener("keydown", speciesShortcut));
    onUnmounted(() => window.removeEventListener("keydown", speciesShortcut));

    return {
      search,
      selectedCode,
      groupedItems,
      customFilter,
      categoryColors,
      speciesAutocomplete,
    };
  },
});
</script>

<template>
  <div class="d-flex align-center flex-nowrap single-specie-editor-row">
    <SingleSpecieInfo
      :model-value="selectedCode"
      :species-list="speciesList"
      :disabled="disabled"
      @update:model-value="$emit('update:modelValue', $event)"
    />
    <v-autocomplete
      ref="speciesAutocomplete"
      v-model="selectedCode"
      v-model:search-input="search"
      autocomplete="off"
      :items="groupedItems"
      item-title="species_code"
      item-value="species_code"
      :multiple="false"
      :custom-filter="customFilter"
      clearable
      clear-on-select
      label="Select species"
      :menu-props="{ maxHeight: '300px', maxWidth: '400px' }"
      :disabled="disabled"
      class="species-autocomplete-fill"
      density="compact"
      hide-details
    >
      <template #subheader="{ props: subProps }">
        <v-list-subheader
          class="font-weight-bold"
          :class="
            categoryColors[String(subProps.title).toLowerCase()]
              ? `bg-${categoryColors[String(subProps.title).toLowerCase()]}`
              : ''
          "
        >
          {{ subProps.title }}
        </v-list-subheader>
      </template>
      <template #item="{ props: itemProps, item }">
        <v-list-item
          v-bind="itemProps"
          :title="(item.raw as Species).common_name"
        >
          <template #subtitle="{}">
            <span>{{ (item.raw as Species).species_code }}</span>
            <v-chip
              v-if="(item.raw as Species).category"
              :color="categoryColors[(item.raw as Species).category]"
              small
              class="ml-2"
            >
              {{ (item.raw as Species).category }}
            </v-chip>
          </template>
        </v-list-item>
      </template>
    </v-autocomplete>
    <v-btn
      v-if="showDelete"
      icon
      size="x-small"
      variant="text"
      color="error"
      :disabled="disabled"
      class="ml-1"
      v-tooltip="'Delete species'"
      @click="$emit('delete')"
    >
      <v-icon>mdi-delete</v-icon>
    </v-btn>
  </div>
</template>

<style scoped>
.single-specie-editor-row {
  min-width: 0;
  width: 100%;
}
.species-autocomplete-fill {
  flex: 1 1 0;
  min-width: 0;
}
</style>
