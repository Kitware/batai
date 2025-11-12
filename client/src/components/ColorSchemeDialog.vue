<script setup lang="ts">
import { onMounted, watch } from 'vue';
import useState from '@use/useState';
import ColorSchemeSelect from './ColorSchemeSelect.vue';
import ColorPickerMenu from './ColorPickerMenu.vue';

const {
  configuration,
  colorSchemes,
  colorScheme,
  backgroundColor,
} = useState();

onMounted(() => {
  const localBackgroundColor = localStorage.getItem('spectrogramBackgroundColor');
  if (localBackgroundColor) {
    backgroundColor.value = localBackgroundColor;
  } else {
    backgroundColor.value = configuration.value.default_spectrogram_background_color || 'rgb(0, 0, 0)';
  }
  const localColorScheme = localStorage.getItem('spectrogramColorScheme');
  if (localColorScheme) {
    colorScheme.value = colorSchemes.find((scheme) => scheme.value === localColorScheme) || colorSchemes[0];
  } else if (configuration.value.default_color_scheme) {
    colorScheme.value = colorSchemes.find((scheme) => scheme.value === configuration.value.default_color_scheme) || colorSchemes[0];
  }
});

watch(backgroundColor, () => {
  localStorage.setItem('spectrogramBackgroundColor', backgroundColor.value);
});
watch(colorScheme, () => {
  localStorage.setItem('spectrogramColorScheme', colorScheme.value.value);
});
</script>

<template>
  <v-dialog max-width="300">
    <template #activator="{ props: modalProps }">
      <v-tooltip>
        <template #activator="{ props: tooltipProps }">
          <v-icon
            v-bind="{ ...modalProps, ...tooltipProps }"
            size="25"
          >
            mdi-palette
          </v-icon>
        </template>
        View spectrogram color options
      </v-tooltip>
    </template>
    <template #default="{ isActive }">
      <v-card>
        <v-card-title>
          Spectrogram Color Options
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="8">
              <color-scheme-select
                v-model="colorScheme"
                label="Color Scheme"
                :color-schemes="colorSchemes"
                class="pt-3"
              />
            </v-col>
            <v-col cols="4">
              <color-picker-menu
                v-model="backgroundColor"
                tooltip-text="Spectrogram background color"
              />
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-btn
            text="Close"
            @click="isActive.value = false"
          />
        </v-card-actions>
      </v-card>
    </template>
  </v-dialog>
</template>
