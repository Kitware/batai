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
  </v-card>
</template>
