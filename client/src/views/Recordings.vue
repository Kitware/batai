<script lang="ts">
import { defineComponent, ref, Ref, onMounted } from 'vue';
import { getRecordings, Recording } from '../api/api';
import {
  VDataTable,
} from "vuetify/labs/VDataTable";
import UploadRecording from '../components/UploadRecording.vue';

export default defineComponent({
    components: {
        VDataTable,
        UploadRecording,
    },
  setup() {
    const itemsPerPage = ref(-1);
    const recordingList: Ref<Recording[]> = ref([]);
    const uploadDialog = ref(false);
    const headers = ref([
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
            title:'Equipment',
            key:'equipment',
        },
        {
            title:'Comments',
            key:'comments',
        },
    ]);

    const fetchRecordings = async () => {
        const recordings = await getRecordings();
        recordingList.value = recordings.data;
    };
    onMounted(() => fetchRecordings());

    const uploadDone = () => {
        uploadDialog.value = false;
        fetchRecordings();
    };

    return {
        itemsPerPage,
        headers,
        recordingList,
        uploadDialog,
        uploadDone,
     };
  },
});
</script>

<template>
  <v-card>
    <v-card-title>
      <v-row class="py-2">
        <div>
          Recordings
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
        <template #item.name="{ item }">
          <div>
            {{ item.raw.name }}
          </div>
          <router-link
            v-if="false"
            :to="`/recording/${item.id}`"
          >
            {{ item.name }}
          </router-link>
        </template>
      </v-data-table>
    </v-card-text>
    <v-dialog
      v-model="uploadDialog"
      width="400"
    >
      <upload-recording  @done="uploadDone()"/>
    </v-dialog>
  </v-card>
</template>
