<script setup lang="ts">
import { defineModel } from 'vue';

defineProps({
  colorSchemes: {
    type: Array as () => { value: string; title: string; scheme: (input: number) => string }[],
    required: true,
  },
  label: {
      type: String,
      default: 'Color Scheme',
  },
  width: {
    type: Number,
    default: 150,
  },
  returnObject: {
    type: Boolean,
    default: true,
  }
});

const colorScheme = defineModel();
</script>

<template>
  <v-select
    v-model="colorScheme"
    :label="label"
    :items="colorSchemes"
    item-title="title"
    item-value="value"
    variant="outlined"
    density="compact"
    :return-object="returnObject"
    hide-details
    :style="`max-width: ${maxWidth}px; min-width: ${maxWidth}px`"
  >
    <template #item="{ item, props }">
      <div
        v-bind="props"
        class="custom-hover"
      >
        <v-row
          dense
          align="center"
          justify="center"
          no-gutters
        >
          <span>{{ item.title }}</span>
        </v-row>
        <v-row
          dense
          no-gutters
          align="center"
          justify="center"
          class="pb-2 px-2"
        >
          <div
            v-for="n in 11"
            :key="n"
            size="10"
            :style="{ backgroundColor: item.raw.scheme((n - 1) / 10) }"
            class="color-swatch"
          />
        </v-row>
      </div>
      <v-divider />
    </template>

    <template #selection="{ item }">
      <div class="d-flex align-center">
        <span>{{ item.title }}</span>
      </div>
    </template>
  </v-select>
</template>

<style scoped>
.color-swatch {
  width:15px;
  height: 10px;
}
.custom-hover {
  cursor: pointer;
}
.custom-hover:hover {
  font-weight: bold;;
}
</style>
