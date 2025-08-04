<script lang="ts">
import { defineComponent, PropType, computed, ref, watch } from 'vue';
import { Species } from '@api/api';

export default defineComponent({
  name: 'SpeciesEditor',
  props: {
    modelValue: {
      type: Array as PropType<string[]>,
      default: () => [],
    },
    speciesList: {
      type: Array as PropType<Species[]>,
      default: () => [],
    },
  },
  emits: ['update:modelValue'],

  setup(props, { emit }) {
    const search = ref('');

    // Used internally to track selected species by ID
    const selectedNames = ref<string[]>(props.modelValue);

    // Update selected IDs when v-model changes from outside
    watch(() => props.modelValue, (newVal) => {
      selectedNames.value = newVal;
    }, { immediate: true });

    // Emit updated species objects when selection changes
    watch(selectedNames, (newNames) => {
      const selectedSpecies = props.speciesList.filter(s => newNames.includes(s.species_code));
      emit('update:modelValue', selectedSpecies.map((item) => item.species_code));
    });

    // Prepare items with headers inserted by category
    const groupedItems = computed(() => {
      const groups: Record<string, Species[]> = {};
      for (const s of props.speciesList) {
        const cat = s.category.charAt(0).toUpperCase() + s.category.slice(1); // Capitalize
        if (!groups[cat]) groups[cat] = [];
        groups[cat].push(s);
      }

      const result: Array<{ type: 'subheader', title: string } | Species> = [];
      Object.entries(groups).forEach(([key, category]) => {
        result.push({ type: 'subheader', title: key });
        result.push(...category);
      });


      return result;
    });

    return {
      search,
      selectedNames,
      groupedItems,
    };
  },
});
</script>

<template>
  <v-autocomplete
    v-model="selectedNames"
    v-model:search-input="search"
    :items="groupedItems"
    item-title="common_name"
    item-value="species_code"
    multiple
    chips
    closable-chips
    clearable
    label="Select Species"
    :menu-props="{ maxHeight: '300px' }"
  >
    <template #subheader="{ props }">
      <v-list-subheader class="font-weight-bold bg-primary">
        {{ props.title }}
      </v-list-subheader>
    </template>
    <template #chip="{ props, item }">
      <v-chip
        v-if="item.raw.value"
        v-bind="props"
        :text="item.raw.species_code"
      />
    </template>
  </v-autocomplete>
</template>

<style scoped>
/* Optional custom styling */
</style>
