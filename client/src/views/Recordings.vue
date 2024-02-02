<script lang="ts">
import { defineComponent, ref, Ref, onMounted } from 'vue';
import { getRecordings, Recording } from '../api/api';
import {
  VDataTable,
} from "vuetify/labs/VDataTable";
import UploadRecording, { EditingRecording } from '../components/UploadRecording.vue';
import MapLocation from '../components/MapLocation.vue';

export default defineComponent({
    components: {
        VDataTable,
        UploadRecording,
        MapLocation,
    },
  setup() {
    const itemsPerPage = ref(-1);
    const recordingList: Ref<Recording[]> = ref([]);
    const sharedList: Ref<Recording[]> = ref([]);
    const editingRecording: Ref<EditingRecording | null> = ref(null);

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
        const [ lat, lon ] = item.recording_location.coordinates;
        editingRecording.value['location'] = {lat, lon};
      }
      uploadDialog.value = true;
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
        class="elevation-1"
      >
        <template #item.edit="{ item }">
          <v-icon @click="editRecording(item.raw)">
            mdi-pencil
          </v-icon>
        </template>

        <template #item.name="{ item }">
          <router-link
            :to="`/recording/${item.raw.id.toString()}/spectrogram`"
          >
            {{ item.raw.name }}
          </router-link>
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
          <v-icon v-else color="error">
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
        class="elevation-1"
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
          <v-icon v-else color="error">
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
      </v-data-table>
    </v-card-text>
  </v-card>
</template>
