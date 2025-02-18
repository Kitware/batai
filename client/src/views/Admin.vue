 
  <script>
  import { reactive, defineComponent, watch } from 'vue';
import useState from '../use/useState';
import { patchConfiguration } from '../api/api';
  
  export default defineComponent({
    name: 'Admin',
    setup() {
      // Reactive state for the settings
      const  { configuration, loadConfiguration } = useState();
      const settings = reactive({
        displayPulseAnnotations: configuration.value.display_pulse_annotations,
        displaySequenceAnnotations: configuration.value.display_sequence_annotations,
      });
      watch(configuration, () => {
        settings.displayPulseAnnotations = configuration.value.display_pulse_annotations;
        settings.displaySequenceAnnotations = configuration.value.display_sequence_annotations;
      });
      // Function to save the settings
      const saveSettings = async () => {
        // Mock save function: replace with API call if necessary
        await patchConfiguration( {
            display_pulse_annotations: settings.displayPulseAnnotations,
            display_sequence_annotations: settings.displaySequenceAnnotations
        });
        loadConfiguration();
      };
  
      return {
        settings,
        saveSettings,
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
  