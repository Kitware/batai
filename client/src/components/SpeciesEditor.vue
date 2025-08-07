<script lang="ts">
import { defineComponent, PropType, computed, ref, watch, Ref } from 'vue';
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
    const speciesAutocomplete: Ref<HTMLElement | null> = ref(null);

    // Update selected IDs when v-model changes from outside
    watch(() => props.modelValue, (newVal) => {
      if (newVal !== props.modelValue) {
        selectedNames.value = props.modelValue;
      }
    }, { immediate: true });

    // Emit updated species objects when selection changes
    watch(selectedNames, (newNames) => {
      emit('update:modelValue', newNames);
      // Hides the auto-complete menu after making a single selection
      requestAnimationFrame(() => {
        if (speciesAutocomplete.value) {
          speciesAutocomplete.value?.blur();
        }
      });
    });

    const categoryColors: Record<string, string> =  {
      'individual': 'primary',
      'couplet': 'secondary',
      'frequency': 'warning',
      'noid': '',
    };

    // Prepare items with headers inserted by category
    const groupedItems = computed(() => {
      const groups: Record<string, Species[]> = {};
      for (const s of props.speciesList) {
        const cat = s.category.charAt(0).toUpperCase() + s.category.slice(1); // Capitalize
        if (!groups[cat]) groups[cat] = [];
        groups[cat].push(s);
      }

      const result: Array<{ type: 'subheader', title: string } | Species & { category: string}> = [];
      const groupsOrder = ['Individual', 'Couplet', 'Frequency', 'Noid'];
      groupsOrder.forEach((key) => {
        result.push({ type: 'subheader', title: key });
        result.push(...(groups[key]));
      });

      return result;
    });
    const customFilter = (filter: string, search: string, item: any) => {
      if (item.type === 'subheader') {
        return false;
      }
      const search_lower = search.toLocaleLowerCase();
      return item.raw.species_code.toLocaleLowerCase().includes(search_lower) || item.raw.common_name.toLocaleLowerCase().includes(search_lower);
    };

    const removeChip = (event: PointerEvent, item: Species) => {
      event.preventDefault();
      event.stopPropagation();
      const index = selectedNames.value.findIndex((species) => species === item.species_code);
      if (index !== -1) {
        selectedNames.value.splice(index, 1);
        emit('update:modelValue', selectedNames.value);
      }
    };

    return {
      search,
      selectedNames,
      groupedItems,
      customFilter,
      categoryColors,
      removeChip,
      speciesAutocomplete,
    };
  },
});
</script>

<template>
  <v-autocomplete
    ref="speciesAutocomplete"
    v-model="selectedNames"
    v-model:search-input="search"
    :items="groupedItems"
    item-title="species_code"
    item-value="species_code"
    multiple
    chips
    closable-chips
    :custom-filter="customFilter"
    clearable
    label="Select Labels"
    :menu-props="{ maxHeight: '300px', maxWidth: '400px' }"
  >
    <template #subheader="{ props }">
      <v-list-subheader
        class="font-weight-bold"
        :class="categoryColors[props.title.toLowerCase()] ? `bg-${categoryColors[props.title.toLowerCase()]}` : ''"
      >
        {{ props.title }}
      </v-list-subheader>
    </template>
    <template #item="{ props, item }">
      <v-list-item
        v-bind="props"
        :subtitle="item.raw.species_code"
        :title="item.raw.common_name"
      />
    </template>
    <template #chip="{item}">
      <v-tooltip
        location="bottom"
        open-delay="100"
      >
        <template #activator="{ props }">
          <v-chip
            v-bind="props"
            :color="categoryColors[item.raw.category]"
            @click:close="removeChip($event, item.raw)"
            @mousedown.stop.prevent
          >
            {{ item.raw.species_code }}
          </v-chip>
        </template>
        <v-card class="pa-0 ma-0">
          <v-card-title
            :class="categoryColors[item.raw.category] ? `bg-${categoryColors[item.raw.category]}` : ''"
          >
            {{ item.raw.category.toUpperCase() }}
          </v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item>
                {{ item.raw.species_code }}
              </v-list-item>
              <v-list-item>
                {{ item.raw.common_name }}
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-tooltip>
    </template>
  </v-autocomplete>
</template>

<style scoped>
/* Optional custom styling */
</style>
