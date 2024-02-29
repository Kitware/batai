<script lang="ts">
import { defineComponent, ref, Ref, onMounted } from 'vue';
import { deleteRecording, getRecordings, Recording } from '../api/api';
import {
  VDataTable,
} from "vuetify/labs/VDataTable";
import UploadRecording, { EditingRecording } from '../components/UploadRecording.vue';
import MapLocation from '../components/MapLocation.vue';
import useState from '../use/useState';

export default defineComponent({
    components: {
        VDataTable,
        UploadRecording,
        MapLocation,
    },
  setup() {
    const itemsPerPage = ref(-1);
    const { sharedList, recordingList } = useState();
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
            title:'Recorded Time',
            key:'recorded_time',
        },
        {
            title:'Public',
            key:'public',
        },
        {
            title:'GRTS CellId',
            key:'grts_cell_id',
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
            title:'Recorded Time',
            key:'recorded_time',
        },
        {
            title:'Public',
            key:'public',
        },
        {
            title:'GRTS CellId',
            key:'grts_cell_id',
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
        time: item.recorded_time,
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
  <v-card>
    <v-card-title>
      <v-row class="py-2">
        <div>
          My Recordings
        </div>
        <v-spacer />
        <v-btn 
          color="primary"
          @click="uploadDialog=true"
        >
          Upload <v-icon> mdi-plus</v-icon>
        </v-btn>
      </v-row>
    </v-card-title>
    <v-card-text>
      <v-data-table
        v-model:items-per-page="itemsPerPage"
        :headers="headers"
        :items="recordingList"
        density="compact"
        class="elevation-1 my-recordings"
      >
        <template #item.edit="{ item }">
          <v-icon @click="editRecording(item.raw)">
            mdi-pencil
          </v-icon>
          <v-icon
            color="error"
            @click="delRecording(item.raw.id)"
          >
            mdi-delete
          </v-icon>
        </template>

        <template #item.name="{ item }">
          <router-link
            v-if="item.raw.hasSpectrogram"
            :to="`/recording/${item.raw.id.toString()}/spectrogram`"
          >
            {{ item.raw.name }}
          </router-link>
          <div v-else>
            {{ item.raw.name }} 
            <v-tooltip bottom>
              <template #activator="{ props: subProps }">
                <span v-bind="subProps">
                  <v-icon color="warning">mdi-alert</v-icon>
                  <v-icon>mdi-sync mdi-spin</v-icon>
                </span>
              </template>
              <span>Waiting for spectrogram to be computed</span>
            </v-tooltip>
          </div>
        </template>
        <template #item.recording_location="{ item }">
          <v-menu
            v-if="item.raw.recording_location"
            open-on-hover
          >
            <template #activator="{ props }">
              <v-icon v-bind="props">
                mdi-map
              </v-icon>
            </template>
            <v-card>
              <map-location
                :editor="false"
                :size="{width: 400, height: 400}"
                :location="{ x: item.raw.recording_location.coordinates[0], y: item.raw.recording_location.coordinates[1]}"
              />
            </v-card>
          </v-menu>
          <v-icon
            v-else
            color="error"
          >
            mdi-close
          </v-icon>
        </template>

        <template #item.public="{ item }">
          <v-icon
            v-if="item.raw.public"
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
        </template>
        <template #bottom />
      </v-data-table>
    </v-card-text>
    <v-dialog
      v-model="uploadDialog"
      width="700"
    >
      <upload-recording
        :editing="editingRecording"
        @done="uploadDone()"
        @cancel="uploadDialog = false; editingRecording = null"
      />
    </v-dialog>
  </v-card>
  <v-card>
    <v-card-title>
      <v-row class="py-2">
        <div>
          Shared
        </div>
      </v-row>
    </v-card-title>
    <v-card-text>
      <v-data-table
        v-model:items-per-page="itemsPerPage"
        :headers="sharedHeaders"
        :items="sharedList"
        density="compact"
        class="elevation-1 shared-recordings"
      >
        <template #item.name="{ item }">
          <router-link
            :to="`/recording/${item.raw.id.toString()}/spectrogram`"
          >
            {{ item.raw.name }}
          </router-link>
        </template>
        <template #item.public="{ item }">
          <v-icon
            v-if="item.raw.public"
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
        </template>
        <template #item.recording_location="{ item }">
          <v-menu
            v-if="item.raw.recording_location"
            open-on-hover
          >
            <template #activator="{ props }">
              <v-icon v-bind="props">
                mdi-map
              </v-icon>
            </template>
            <v-card>
              <map-location
                :editor="false"
                :size="{width: 400, height: 400}"
                :location="{ x: item.raw.recording_location.coordinates[0], y: item.raw.recording_location.coordinates[1]}"
              />
            </v-card>
          </v-menu>
          <v-icon
            v-else
            color="error"
          >
            mdi-close
          </v-icon>
        </template>

        <template #item.userMadeAnnotations="{ item }">
          <v-icon
            v-if="item.raw.userMadeAnnotations"
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
        </template>
        <template #bottom />
      </v-data-table>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.my-recordings {
  height: 40vh;
  max-height: 40vh;
  overflow-y:scroll;
}
.shared-recordings {
  height: 40vh;
  max-height: 40vh;
  overflow-y:scroll;
}
</style>