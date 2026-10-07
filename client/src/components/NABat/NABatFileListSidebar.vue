<script lang="ts">
import { defineComponent, onMounted, onUnmounted, ref, type Ref } from "vue";
import { useRouter } from "vue-router";
import { getNABatFileList, type NABatFileListItemInfo } from "@api/NABatApi";
import useNABatFileListQueue from "@/use/useNABatFileListQueue";

const STATUS_COLORS: Record<string, string> = {
  exists: "success",
  queued: "info",
  failed: "error",
  does_not_exist: "grey",
};

const STATUS_LABELS: Record<string, string> = {
  exists: "Ready",
  queued: "In progress",
  failed: "Failed",
  does_not_exist: "Not started",
};

// Lets a user browse/jump between a file list's items from within the
// spectrogram view - the counterpart to RecordingList.vue for file lists.
// Polls the list's status periodically so other items' progress stays visible
// even while the user isn't actively waiting on one of them - but only while
// something's actually queued, so an idle tab left open on this view doesn't
// keep hitting the backend (and holding a DB connection) forever.
const POLL_INTERVAL_MS = 5000;

export default defineComponent({
  props: {
    fileListId: {
      type: Number,
      required: true,
    },
    currentId: {
      type: String,
      required: true,
    },
  },
  emits: ["queue-start", "queue-progress", "queue-end"],
  setup(props, { emit }) {
    const router = useRouter();
    const { queuePositionAndWait } = useNABatFileListQueue();
    const items: Ref<NABatFileListItemInfo[]> = ref([]);
    const errorMessage: Ref<string | null> = ref(null);
    const switchingPosition: Ref<number | null> = ref(null);
    let pollTimeoutId: ReturnType<typeof setTimeout> | null = null;
    // Bumped on every click; a stale in-flight request (superseded by a later
    // click before it resolved) checks this before touching shared state, so an
    // abandoned wait can't navigate or emit anything once something newer has
    // taken over - without needing to disable the rest of the list meanwhile.
    let requestToken = 0;

    function formatDate(isoString: string | null): string {
      if (!isoString) return "";
      const date = new Date(isoString);
      return new Intl.DateTimeFormat("en-CA", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      })
        .format(date)
        .replace(",", "");
    }

    async function refresh() {
      try {
        const status = await getNABatFileList(props.fileListId);
        items.value = status.items;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } catch (error: any) {
        errorMessage.value =
          error.response?.data?.error ?? `Failed to load file list: ${error}`;
      }
    }

    function stopPolling() {
      if (pollTimeoutId !== null) {
        clearTimeout(pollTimeoutId);
        pollTimeoutId = null;
      }
    }

    // `force` schedules one poll regardless of current status - used right after
    // dispatching a queue request, since `items` won't show it as "queued" until
    // that poll actually runs. Every poll after that reschedules itself only if
    // something's still queued, so it naturally stops once everything settles.
    function scheduleNextPoll(force = false) {
      stopPolling();
      if (!force && !items.value.some((item) => item.status === "queued")) {
        return;
      }
      pollTimeoutId = setTimeout(async () => {
        await refresh();
        scheduleNextPoll();
      }, POLL_INTERVAL_MS);
    }

    async function openItem(item: NABatFileListItemInfo, position: number) {
      const myToken = ++requestToken;

      // Both branches below clear switchingPosition (the stale highlight) and
      // emit queue-end (the parent's big spinner) explicitly, left over from a
      // previous click still "waiting" - that click's own finally/watch-based
      // reset no-ops once a newer click (this one) has moved requestToken past
      // it, and the first branch especially has no route change of its own to
      // otherwise trigger NABatSpectrogram.vue's reset.
      if (item.nabatRecordingId?.toString() === props.currentId) {
        switchingPosition.value = null;
        emit("queue-end");
        return;
      }
      if (item.status === "exists" && item.nabatRecordingId) {
        switchingPosition.value = null;
        emit("queue-end");
        router.push(
          `/nabat/${item.nabatRecordingId}/spectrogram?fileListId=${props.fileListId}`,
        );
        return;
      }
      errorMessage.value = null;
      switchingPosition.value = position;
      emit("queue-start");
      emit("queue-progress", "Queuing...");
      scheduleNextPoll(true);
      try {
        const recordingId = await queuePositionAndWait(
          props.fileListId,
          position,
          () => myToken !== requestToken,
          (description) => {
            if (myToken === requestToken) {
              emit("queue-progress", description);
            }
          },
        );
        if (myToken !== requestToken) {
          return;
        }
        router.push(
          `/nabat/${recordingId}/spectrogram?fileListId=${props.fileListId}`,
        );
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } catch (error: any) {
        if (myToken !== requestToken) {
          return;
        }
        errorMessage.value =
          error.message ?? `Failed to process item: ${error}`;
        emit("queue-end");
        await refresh();
      } finally {
        if (myToken === requestToken) {
          switchingPosition.value = null;
        }
      }
    }

    onMounted(async () => {
      await refresh();
      scheduleNextPoll();
    });

    onUnmounted(() => {
      stopPolling();
    });

    return {
      items,
      errorMessage,
      switchingPosition,
      openItem,
      formatDate,
      statusColor: (status: string) => STATUS_COLORS[status] ?? "grey",
      statusLabel: (status: string) => STATUS_LABELS[status] ?? status,
    };
  },
});
</script>
<template>
  <div>
    <v-alert v-if="errorMessage" type="error" density="compact" class="mb-2">
      {{ errorMessage }}
    </v-alert>
    <v-list density="compact">
      <v-list-item
        v-for="(item, position) in items"
        :key="item.id"
        :class="{
          'nabat-file-list-current':
            switchingPosition === position ||
            (switchingPosition === null &&
              item.nabatRecordingId?.toString() === currentId),
        }"
        @click="openItem(item, position)"
      >
        <v-list-item-title>{{ item.fileName }}</v-list-item-title>
        <v-list-item-subtitle>{{
          formatDate(item.recordingTime)
        }}</v-list-item-subtitle>
        <template #append>
          <v-progress-circular
            v-if="switchingPosition === position"
            indeterminate
            size="20"
            width="2"
          />
          <v-chip v-else :color="statusColor(item.status)" size="small">
            {{ statusLabel(item.status) }}
          </v-chip>
        </template>
      </v-list-item>
    </v-list>
  </div>
</template>

<style scoped>
.nabat-file-list-current {
  border: 2px solid rgb(var(--v-theme-primary));
  box-sizing: border-box;
}
</style>
