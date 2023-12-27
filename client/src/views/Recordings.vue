<script lang="ts">
import { defineComponent, ref, Ref, onMounted } from 'vue';
import { getRecordings, Recording } from '../api/api';
import {
  VDataTable,
} from "vuetify/labs/VDataTable";

export default defineComponent({
    components: {
        VDataTable,
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
            key:'owner_usename',
        },
        {
            title:'Date',
            key:'recording_date',
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
        console.log('fetching recordings');
        const recordings = await getRecordings();
        recordingList.value = recordings.data;
    };
    onMounted(() => fetchRecordings());

    return {
        itemsPerPage,
        headers,
        recordingList,
        uploadDialog,
     };
  },
});
</script>

<template>
<v-card>
    <v-card-title>
      Recordings
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
          <router-link :to="`/recording/${item.id}`">
            {{ item.name }}</router-link>
        </template>
      </v-data-table>
    </v-card-text>
  </v-card>
</template>
