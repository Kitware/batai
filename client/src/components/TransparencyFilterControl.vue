<script lang="ts">
import { defineComponent } from "vue";
import useState from "@use/useState";

export default defineComponent({
  name: "TransparencyFilterControl",
  setup() {
    const { transparencyThreshold } = useState();

    return {
      transparencyThreshold,
    };
  },
});
</script>

<template>
  <v-menu
    location="bottom"
    :close-on-content-click="false"
    open-on-hover
  >
    <template #activator="{ props: menuProps }">
      <v-badge
        :content="`${transparencyThreshold}%`"
        :model-value="transparencyThreshold > 0"
        location="bottom right"
        color="primary"
        :offset-x="10"
      >
        <v-icon
          v-bind="menuProps"
          size="30"
          class="mx-3"
          :color="transparencyThreshold > 0 ? 'blue' : ''"
        >
          mdi-opacity
        </v-icon>
      </v-badge>
    </template>
    <v-card
      min-width="200"
    >
      <v-card-title class="text-subtitle-1">
        Noise Filter {{ transparencyThreshold }}%
      </v-card-title>
      <v-card-text>
        <p>Removes low-intensity background noise in the spectrogram</p>
        <v-slider
          v-model="transparencyThreshold"
          min="0"
          max="100"
          step="1"
          track-color="grey"
          color="primary"
          hide-details
        >
          <template #thumb-label="{ modelValue }">
            {{ modelValue }}%
          </template>
        </v-slider>
      </v-card-text>
    </v-card>
  </v-menu>
</template>
