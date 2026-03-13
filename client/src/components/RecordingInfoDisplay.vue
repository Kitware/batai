<script lang="ts">
import { computed, defineComponent, PropType } from 'vue';
import { Recording } from '../api/api';
import MapLocation from './MapLocation.vue';


export default defineComponent({
  components: {
    MapLocation
  },
  props: {
    recordingInfo: {
      type: Object as PropType<Recording>,
      required: true,
    },
    disableButton: {
      type: Boolean,
      default: false,
    },
    minimalMetadata: {
      type: Boolean,
      default: false,
    },
    displayMode: {
      type: String as PropType<'both' | 'metadata' | 'map'>,
      default: 'both',
    }
  },
  emits: ['close'],
  setup(props) {
    const location = computed(() => {
      if (props.recordingInfo.recording_location) {
        return {
          x: props.recordingInfo.recording_location.coordinates[0],
          y:props.recordingInfo.recording_location.coordinates[1]
        };
      }
      return undefined;
    });
    const showMetadata = computed(() => props.displayMode === 'both' || props.displayMode === 'metadata');
    const showMap = computed(() => props.displayMode === 'both' || props.displayMode === 'map');
    return {
      location,
      showMetadata,
      showMap,
    };
  },
});
</script>

<template>
  <v-card v-if="recordingInfo">
    <v-card-title>
      {{ recordingInfo.name }}
    </v-card-title>
    <v-card-text>
      <div v-if="showMetadata">
        <v-row>
          <div><b>Filename:</b><span>{{ recordingInfo.audio_file }}</span></div>
        </v-row>
        <v-row>
          <div><b>Owner:</b><span>{{ recordingInfo.owner_username }}</span></div>
        </v-row>
        <v-row>
          <div><b>Time:</b><span>{{ recordingInfo.recorded_date }}</span> <span> {{ recordingInfo.recorded_time }}</span></div>
        </v-row>
        <v-row v-if="!minimalMetadata">
          <div><b>Equipment:</b><span>{{ recordingInfo.equipment || 'None' }}</span></div>
        </v-row>
        <v-row v-if="!minimalMetadata">
          <div><b>Comments:</b><span>{{ recordingInfo.comments || 'None' }}</span></div>
        </v-row>
      </div>
      <v-row
        v-if="recordingInfo.grts_cell_id && showMetadata && displayMode === 'both' || displayMode === 'metadata'"
        class="mt-2"
      >
        <div><b>GRTS CellId:</b><span>{{ recordingInfo.grts_cell_id }}</span></div>
      </v-row>
      <v-row
        v-if="recordingInfo.recording_location && showMap"
        class="justify-center"
      >
        <map-location
          :editor="false"
          :size="{width: 400, height: 400}"
          :location="location"
          :grts-cell-id="recordingInfo.grts_cell_id || undefined"
        />
      </v-row>
      <v-row
        v-if="recordingInfo.grts_cell_id && !showMetadata && showMap"
        class="justify-center mt-4"
      >
        <div class="text-center">
          <b>GRTS CellId:</b>
          <span>{{ recordingInfo.grts_cell_id }}</span>
        </div>
      </v-row>

      <div
        v-if="recordingInfo.site_name && showMetadata"
        class="mt-5"
      >
        <v-row><h3>Guano Metadata</h3></v-row>
        <v-row v-if="recordingInfo.site_name">
          <div><b>Site Name:</b><span>{{ recordingInfo.site_name }}</span></div>
        </v-row>
        <v-row v-if="recordingInfo.software">
          <div><b>Software:</b><span>{{ recordingInfo.software }}</span></div>
        </v-row>
        <v-row v-if="recordingInfo.detector">
          <div><b>Detector:</b><span>{{ recordingInfo.detector }}</span></div>
        </v-row>
        <v-row v-if="recordingInfo.species_list">
          <div><b>Species List:</b><span>{{ recordingInfo.species_list }}</span></div>
        </v-row>
        <v-row v-if="recordingInfo.unusual_occurrences">
          <div><b>Unusual Occurrences:</b><span>{{ recordingInfo.unusual_occurrences }}</span></div>
        </v-row>
      </div>
    </v-card-text>
    <v-card-actions v-if="!disableButton">
      <v-row>
        <v-spacer />
        <v-btn
          variant="outlined"
          @click="$emit('close')"
        >
          OK
        </v-btn>
        <v-spacer />
      </v-row>
    </v-card-actions>
  </v-card>
</template>
