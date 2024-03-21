<script lang="ts">
import { defineComponent, onMounted, ref, Ref, watch } from 'vue';
import { getRecording, Recording } from '../api/api';
import MapLocation from './MapLocation.vue';


export default defineComponent({
  components: {
    MapLocation
  },
  props: {
    id: {
      type: String,
      required: true,
    },
  },
  emits: ['close'],
  setup(props) {
    const recordingInfo: Ref<Recording | null> = ref(null);

    const loadData = async () => {
      const recording = getRecording(props.id);
      recordingInfo.value = (await recording).data;
    };
    watch(() => props.id, () => loadData());
    onMounted(() => loadData());
    return {
      recordingInfo,
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
      <v-row>
        <div><b>Filename:</b><span>{{ recordingInfo.audio_file }}</span></div>
      </v-row>
      <v-row>
        <div><b>Owner:</b><span>{{ recordingInfo.owner_username }}</span></div>
      </v-row>
      <v-row>
        <div><b>Time:</b><span>{{ recordingInfo.recorded_date }}</span> <span> {{ recordingInfo.recorded_time }}</span></div>
      </v-row>
      <v-row>
        <div><b>Equipment:</b><span>{{ recordingInfo.equipment || 'None' }}</span></div>
      </v-row>
      <v-row>
        <div><b>Comments:</b><span>{{ recordingInfo.comments || 'None' }}</span></div>
      </v-row>
      <v-row>
        <div><b>GRTS CellId:</b><span>{{ recordingInfo.grts_cell_id }}</span></div>
      </v-row>
      <v-row v-if="recordingInfo.recording_location">
        <v-spacer />
        <map-location
          :editor="false"
          :size="{width: 400, height: 400}"
          :location="{ x: recordingInfo.recording_location.coordinates[0], y:recordingInfo.recording_location.coordinates[1]}"
        />
        <v-spacer />
      </v-row>
    </v-card-text>
    <v-card-actions>
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
