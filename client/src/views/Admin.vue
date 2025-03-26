<script>
import { reactive, defineComponent, watch } from 'vue';
import useState from '../use/useState';
import { patchConfiguration } from '../api/api';

export default defineComponent({
  name: 'Admin',
  setup() {
    // Reactive state for the settings
    const { configuration, loadConfiguration } = useState();
    const settings = reactive({
      displayPulseAnnotations: configuration.value.display_pulse_annotations,
      displaySequenceAnnotations: configuration.value.display_sequence_annotations,
      runInferenceOnUpload: configuration.value.run_inference_on_upload,
      spectrogramXStretch: configuration.value.spectrogram_x_stretch,
      spectrogramView: configuration.value.spectrogram_view,
    });
    const spectrogramViewOptions = [
      { title: 'Compressed', value: 'compressed' },
      { title: 'Uncompressed', value: 'uncompressed' },
    ];
    watch(configuration, () => {
      settings.displayPulseAnnotations = configuration.value.display_pulse_annotations;
      settings.displaySequenceAnnotations = configuration.value.display_sequence_annotations;
      settings.runInferenceOnUpload = configuration.value.run_inference_on_upload;
      settings.spectrogramXStretch = configuration.value.spectrogram_x_stretch;
      settings.spectrogramView = configuration.value.spectrogram_view;
    });
    // Function to save the settings
    const saveSettings = async () => {
      // Mock save function: replace with API call if necessary
      await patchConfiguration({
        display_pulse_annotations: settings.displayPulseAnnotations,
        display_sequence_annotations: settings.displaySequenceAnnotations,
        run_inference_on_upload: settings.runInferenceOnUpload,
        spectrogram_x_stretch: settings.spectrogramXStretch,
        spectrogram_view: settings.spectrogramView,
      });
      loadConfiguration();
    };

    return {
      settings,
      saveSettings,
      spectrogramViewOptions,
    };
  },
});
</script>

<template>
  <v-card>
    <v-card-title>Admin Settings</v-card-title>
    <v-card-text>
      <v-row>
        <v-switch
          v-model="settings.displayPulseAnnotations"
          :color="settings.displayPulseAnnotations ? 'primary' : ''"
          label="Show Pulse Annotations"
        />
      </v-row>
      <v-row>
        <v-switch
          v-model="settings.displaySequenceAnnotations"
          :color="settings.displaySequenceAnnotations ? 'primary' : ''"
          label="Show Sequence Annotations"
        />
      </v-row>
      <v-row>
        <v-switch
          v-model="settings.runInferenceOnUpload"
          :color="settings.runInferenceOnUpload ? 'primary' : ''"
          label="Run Inference on Upload"
        />
      </v-row>
      <v-row>
        <v-col cols="3">
          <v-text-field
            v-model="settings.spectrogramXStretch"
            density="compact"
            type="number"
            step="0.25"
            min="1"
            max="5"
            label="Stretch spectrogram"
          />
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="3">
          <v-select
            v-model="settings.spectrogramView"
            :items="spectrogramViewOptions"
            item-title="title"
            item-value="value"
            density="compact"
            label="Default spectrogram view"
          />
        </v-col>
      </v-row>
    </v-card-text>
    <v-card-actions>
      <v-row>
        <v-spacer />
        <v-btn
          color="primary"
          variant="outlined"
          class="mx-2"
          @click="saveSettings"
        >
          Save
        </v-btn>
      </v-row>
    </v-card-actions>
  </v-card>
</template>
<style scoped>
/* Add optional styling */
.v-container {
  margin-top: 20px;
}
</style>
