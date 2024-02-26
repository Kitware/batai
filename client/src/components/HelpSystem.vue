<script lang="ts">
import { defineComponent } from 'vue';
export default defineComponent({
  components: {
  },
  setup() {

    return { };
  },
});
</script>

<template>
  <v-card>
    <v-expansion-panels>
      <v-expansion-panel>
        <v-expansion-panel-title>Controls/Shortcuts</v-expansion-panel-title>
        <v-expansion-panel-text>
          <h4> Controls </h4>
          <v-row>
            <v-col>
              Shortcut
            </v-col>
            <v-col>Description</v-col>
          </v-row>
          <v-row>
            <v-col>left click</v-col>
            <v-col>Select an Annotation</v-col>
          </v-row>
          <v-row>
            <v-col>left click and move</v-col>
            <v-col>Pan spectrogram</v-col>
          </v-row>
          <v-row>
            <v-col>mousewheel</v-col>
            <v-col>Zoom In/Out on the spectrogram</v-col>
          </v-row>
          <v-row>
            <v-col>right click</v-col>
            <v-col>Set Annotation into Editing mode</v-col>
          </v-row>
          <v-row>
            <v-col>ctrl+mousewheel</v-col>
            <v-col>Zoom In/Out on the time scale</v-col>
          </v-row>
          <v-row>
            <v-col>shift+mousewheel</v-col>
            <v-col>Zoom In/Out on the frequency scale</v-col>
          </v-row>
          <h4> Icons</h4>
          <v-row>
            <v-col>
              Icon
            </v-col>
            <v-col>Description</v-col>
          </v-row>
          <v-row>
            <v-col>
              <v-icon size="35">
                mdi-bat
              </v-icon>>
            </v-col>
            <v-col>Toggle Specie Name Annotations on/off</v-col>
          </v-row>
          <v-row>
            <v-col>
              <v-icon size="35">
                mdi-bat
              </v-icon>>
            </v-col>
            <v-col>Toggle Species Name Annotations on/off</v-col>
          </v-row>

          <v-row>
            <v-col>
              <v-btn
                size="35"
                color="blue"
              >
                <h3>ms</h3>
              </v-btn>
            </v-col>
            <v-col>Toggle millisecond/timing labels</v-col>
          </v-row>
          <v-row>
            <v-col>
              <v-btn
                size="35"
                color="blue"
              >
                <h3>khz</h3>
              </v-btn>
            </v-col>
            <v-col>Toggle frequency labels</v-col>
          </v-row>

          <v-row>
            <v-col>
              <v-icon size="35">
                mdi-grid
              </v-icon>>
            </v-col>
            <v-col>Toggle grid on/off</v-col>
          </v-row>
          <v-row>
            <v-col>
              <v-icon size="35">
                mdi-calendar-collapse-horizontal
              </v-icon>>
            </v-col>
            <v-col>Swap between norm and compressed view</v-col>
          </v-row>
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel>
        <v-expansion-panel-title>Annotation Creation</v-expansion-panel-title>
        <v-expansion-panel-text> Simple instructions for annotation or video</v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </v-card>
</template>
