<script lang="ts">
import { defineComponent, ref, Ref, onMounted } from 'vue';
import { deleteRecording, getRecordings, Recording } from '../api/api';
import {
  VDataTable,
} from "vuetify/labs/VDataTable";
import  { EditingRecording } from './UploadRecording.vue';
import MapLocation from './MapLocation.vue';

export default defineComponent({
    components: {
        VDataTable,
        MapLocation,
    },
  setup() {
    const itemsPerPage = ref(-1);
    const recordingList: Ref<Recording[]> = ref([]);
    const sharedList: Ref<Recording[]> = ref([]);
    const editingRecording: Ref<EditingRecording | null> = ref(null);
    let intervalRef: number | null = null;

    const uploadDialog = ref(false);
    const headers = ref([
        {
            title:'Edit',
            key:'edit',
        },

        {
            title:'Name',
            key:'name',
        },
        {
            title:'Owner',
            key:'owner_username',
        },
        {
            title:'Recorded Date',
            key:'recorded_date',
        },
        {
            title:'Public',
            key:'public',
        },
        {
          title: 'Location',
          key:'recording_location'
        },
        {
            title:'Equipment',
            key:'equipment',
        },
        {
            title:'Comments',
            key:'comments',
        },
        {
            title:'Users Annotated',
            key:'userAnnotations',
        },
    ]);

    const sharedHeaders = ref([
        {
            title:'Name',
            key:'name',
        },
        {
            title:'Owner',
            key:'owner_username',
        },
        {
            title:'Recorded Date',
            key:'recorded_date',
        },
        {
            title:'Public',
            key:'public',
        },
        {
          title: 'Location',
          key:'recording_location'
        },
        {
            title:'Equipment',
            key:'equipment',
        },
        {
            title:'Comments',
            key:'comments',
        },
        {
            title:'Annotated by Me',
            key:'userMadeAnnotations',
        },
    ]);
    const fetchRecordings = async () => {
        const recordings = await getRecordings();
        recordingList.value = recordings.data;
        // If we have a spectrogram being generated we need to refresh on an interval
        let missingSpectro = false;
        for (let i =0; i< recordingList.value.length; i+=1) {
          if (!recordingList.value[i].hasSpectrogram) {
            missingSpectro = true;
            break;
          }
        }
        if (missingSpectro) {
          if (intervalRef === null) {
            intervalRef = setInterval(() => fetchRecordings(), 5000);
          }
        } else  {
          if (intervalRef !== null) {
            clearInterval(intervalRef);
          }
        }
        const shared = await getRecordings(true);
        sharedList.value = shared.data;

    };
    onMounted(() => fetchRecordings());

    const uploadDone = () => {
        uploadDialog.value = false;
        editingRecording.value = null;
        fetchRecordings();
    };

    const editRecording = (item: Recording) => {
      editingRecording.value = {
        name: item.name,
        equipment: item.equipment || '', 
        comments: item.comments || '',
        date: item.recorded_date,
        public: item.public,
        id: item.id,
      };
      if (item.recording_location) {
        const [ lon, lat ] = item.recording_location.coordinates;
        editingRecording.value['location'] = {lat, lon};
      }
      uploadDialog.value = true;
    };
    const delRecording = async (id: number) => {
        await deleteRecording(id);
        fetchRecordings();
    };

    return {
        itemsPerPage,
        headers,
        sharedHeaders,
        recordingList,
        sharedList,
        uploadDialog,
        uploadDone,
        editRecording,
        delRecording,
        editingRecording,
     };
  },
});
</script>

<template>
  <v-expansion-panels>
    <v-expansion-panel>
      <v-expansion-panel-title>My Recordings</v-expansion-panel-title>
      <v-expansion-panel-text>
        <div>
          <v-row
            dense
            class="text-center"
          >
            <v-col class="text-left">
              <b>Name</b>
            </v-col>
            <v-col><b>Public</b></v-col>
            <v-col><b>Annotations</b></v-col>
          </v-row>
        </div>
        <div
          v-for="item in recordingList"
          :key="`public_${item.id}`"
        >
          <v-row
            dense
            class="text-center"
          >
            <v-col class="text-left">
              <router-link
                :to="`/recording/${item.id.toString()}/spectrogram`"
              >
                {{ item.name }}
              </router-link>
            </v-col>
            <v-col>
              <v-icon
                v-if="item.public"
                color="success"
              >
                mdi-check
              </v-icon>
              <v-icon
                v-else
                color="error"
              >
                mdi-close
              </v-icon>
            </v-col>
            <v-col>
              <div>
                {{ item.userAnnotations }}
              </div>
            </v-col>
          </v-row>
        </div>
      </v-expansion-panel-text>
    </v-expansion-panel>
    <v-expansion-panel>
      <v-expansion-panel-title>Public</v-expansion-panel-title>
      <v-expansion-panel-text class="ma-0 pa-0">
        <div>
          <v-row
            dense
            class="text-center"
          >
            <v-col class="text-left">
              <b>Name</b>
            </v-col>
            <v-col><b>Owner</b></v-col>
            <v-col><b>Annotated</b></v-col>
          </v-row>
        </div>
        <div
          v-for="item in sharedList"
          :key="`public_${item.id}`"
        >
          <v-row
            dense
            class="text-center"
          >
            <v-col class="text-left">
              <router-link
                :to="`/recording/${item.id.toString()}/spectrogram`"
              >
                {{ item.name }}
              </router-link>
            </v-col>
            <v-col>
              <div style="font-size:0.75em">
                {{ item.owner_username }}
              </div>
            </v-col>
            <v-col>
              <div>
                <v-icon
                  v-if="item.userMadeAnnotations"
                  color="success"
                >
                  mdi-check
                </v-icon>
                <v-icon
                  v-else
                  color="error"
                >
                  mdi-close
                </v-icon>
              </div>
            </v-col>
          </v-row>
        </div>
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
</template>

<style scoped>
.v-expansion-panel-text>>> .v-expansion-panel-text__wrap {
  padding: 0 !important;
}

.v-expansion-panel-text__wrapper {
    padding: 0 !important;
}
</style>