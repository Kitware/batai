<script setup lang="ts">
import useState from '@use/useState';
import { SpectrogramView } from '@/constants';

const {
  spectrogramContentMode,
  setSpectrogramContentMode,
  contoursLoading,
} = useState();

const menuItems = [
  {
    title: 'Image only',
    value: 'image' as SpectrogramView,
  },
  {
    title: 'Contours only',
    value: 'contour' as SpectrogramView,
  },
  {
    title: 'Contours and image',
    value: 'both' as SpectrogramView,
  }
];

</script>

<template>
  <v-tooltip>
    <template #activator="{ props: tooltipProps }">
      <v-menu
        location="top"
      >
        <template #activator="{ props }">
          <v-icon
            v-if="!contoursLoading"
            v-bind="{ ...tooltipProps, ...props }"
            size="25"
            :color="spectrogramContentMode !== 'image' ? 'blue': ''"
          >
            mdi-vector-curve
          </v-icon>
          <v-progress-circular
            v-else
            indeterminate
            size="25"
            color="primary"
          />
        </template>
        <v-list>
          <v-list-item
            v-for="item in menuItems"
            :key="item.value"
            :value="item.value"
          >
            <v-list-item-title
              @click="() => setSpectrogramContentMode(item.value)"
            >
              <v-icon
                v-if="item.value === spectrogramContentMode"
                color="primary"
              >
                mdi-check
              </v-icon>
              {{ item.title }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </template>
    Toggle between smooth contours and raw images
  </v-tooltip>
</template>