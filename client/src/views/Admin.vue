<script lang="ts">
import { reactive, defineComponent, watch, ref, Ref, } from 'vue';
import useState from '@use/useState';
import { patchConfiguration } from '../api/api';
import NABatAdmin from './NABat/NABatAdmin.vue';
import ColorPickerMenu from '@components/ColorPickerMenu.vue';
import ColorSchemeSelect from '@components/ColorSchemeSelect.vue';

export default defineComponent({
  name: 'Admin',
  components: {
    NABatAdmin,
    ColorPickerMenu,
    ColorSchemeSelect,
  },
  setup() {
    // Reactive state for the settings
    const tab: Ref<'admin' | 'nabat'> = ref('admin');
    const { colorSchemes, configuration, loadConfiguration } = useState();
    const settings = reactive({
      displayPulseAnnotations: configuration.value.display_pulse_annotations,
      displaySequenceAnnotations: configuration.value.display_sequence_annotations,
      runInferenceOnUpload: configuration.value.run_inference_on_upload,
      spectrogramXStretch: configuration.value.spectrogram_x_stretch,
      spectrogramView: configuration.value.spectrogram_view,
      defaultColorScheme: configuration.value.default_color_scheme,
      defaultBackgroundColor: configuration.value.default_spectrogram_background_color,
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
      settings.defaultColorScheme = configuration.value.default_color_scheme;
      settings.defaultBackgroundColor = configuration.value.default_spectrogram_background_color;
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
        default_color_scheme: settings.defaultColorScheme,
        default_spectrogram_background_color: settings.defaultBackgroundColor,
        spectrogram_view: settings.spectrogramView,
      });
      loadConfiguration();
    };

    return {
      settings,
      saveSettings,
      spectrogramViewOptions,
      tab,
      colorSchemes,
    };
  },
});
</script>

<template>
  <v-card>
    <v-tabs
      v-model="tab"
      class="ma-auto"
    >
      <v-tab
        value="admin"
        size="small"
      >
        General Admin
      </v-tab>
      <v-tab
        value="nabat"
        size="small"
      >
        NABat Admin
      </v-tab>
    </v-tabs>

    <v-window v-model="tab">
      <v-window-item value="admin">
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
              <div class="text-caption">
                Stretch compressed spectrogram
              </div>
              <v-slider
                v-model="settings.spectrogramXStretch"
                density="compact"
                type="number"
                step="0.25"
                :min="1"
                :max="10"
              >
                <template #append>
                  <v-text-field
                    :model-value="settings.spectrogramXStretch"
                    density="compact"
                    width="70"
                    readonly
                    hide-details
                  />
                </template>
              </v-slider>
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
          <v-row>
            <v-col cols="3">
              <color-scheme-select
                v-model="settings.defaultColorScheme"
                :color-schemes="colorSchemes"
                label="Default Color Scheme"
                :return-object="false"
              />
            </v-col>
          </v-row>
          <v-row>
            <v-label
              text="Default Background Color"
              class="px-2"
            />
            <ColorPickerMenu
              v-model="settings.defaultBackgroundColor"
              tooltip-text="Default background color for spectrograms"
            />
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-row>
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
      </v-window-item>
      <v-window-item value="nabat">
        <NABatAdmin />
      </v-window-item>
    </v-window>
  </v-card>
</template>
<style scoped>
/* Add optional styling */
.v-container {
  margin-top: 20px;
}
</style>
