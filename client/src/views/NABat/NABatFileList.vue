<script lang="ts">
import { defineComponent, onMounted, ref, type Ref } from "vue";
import {
  postNABatFileListCreate,
  getNABatFileList,
  postNABatFileListQueue,
  type NABatFileListItemInfo,
  type NABatFileListItemStatus,
} from "@api/NABatApi";

// Placeholder view: lists a file list's items and their status, with manual
// refresh/queue controls, to exercise the file-list flow before a real
// progress UI (one that updates itself, rather than requiring a click) exists.
const STATUS_COLORS: Record<NABatFileListItemStatus, string> = {
  exists: "success",
  queued: "info",
  failed: "error",
  does_not_exist: "grey",
};

export default defineComponent({
  props: {
    fileListId: {
      type: Number,
      required: true,
    },
  },
  setup(props) {
    const loading = ref(true);
    const errorMessage: Ref<string | null> = ref(null);
    const items: Ref<NABatFileListItemInfo[]> = ref([]);
    const queueingPosition: Ref<number | null> = ref(null);

    async function refresh() {
      loading.value = true;
      errorMessage.value = null;
      try {
        const status = await getNABatFileList(props.fileListId);
        items.value = status.items;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } catch (error: any) {
        errorMessage.value = error.response?.data?.error ?? `Failed to load file list: ${error}`;
      } finally {
        loading.value = false;
      }
    }

    async function queueFrom(position: number) {
      queueingPosition.value = position;
      try {
        await postNABatFileListQueue(props.fileListId, position);
        await refresh();
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } catch (error: any) {
        errorMessage.value = error.response?.data?.error ?? `Failed to queue item: ${error}`;
      } finally {
        queueingPosition.value = null;
      }
    }

    onMounted(async () => {
      try {
        await postNABatFileListCreate(props.fileListId);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } catch (error: any) {
        errorMessage.value = error.response?.data?.error ?? `Failed to create file list: ${error}`;
        loading.value = false;
        return;
      }
      await refresh();
    });

    return {
      loading,
      errorMessage,
      items,
      queueingPosition,
      refresh,
      queueFrom,
      statusColor: (status: NABatFileListItemStatus) => STATUS_COLORS[status] ?? "grey",
    };
  },
});
</script>
<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      NABat File List {{ fileListId }}
      <v-btn class="ml-4" size="small" :loading="loading" @click="refresh"> Refresh </v-btn>
    </v-card-title>
    <v-card-text>
      <v-alert v-if="errorMessage" type="error" class="mb-4">
        {{ errorMessage }}
      </v-alert>
      <v-progress-circular v-if="loading && !items.length" indeterminate color="primary" />
      <v-list v-else>
        <v-list-item v-for="(item, position) in items" :key="item.id">
          <template #prepend>
            <span class="mr-2 text-disabled">{{ position }}</span>
          </template>
          <v-list-item-title>{{ item.fileName }}</v-list-item-title>
          <v-list-item-subtitle>{{ item.recordingTime }}</v-list-item-subtitle>
          <template #append>
            <v-chip :color="statusColor(item.status)" class="mr-2" size="small">
              {{ item.status }}
            </v-chip>
            <v-btn
              size="small"
              :disabled="item.status === 'exists'"
              :loading="queueingPosition === position"
              @click="queueFrom(position)"
            >
              Queue
            </v-btn>
          </template>
        </v-list-item>
      </v-list>
    </v-card-text>
  </v-card>
</template>
