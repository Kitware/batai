import {
  postNABatFileListCreate,
  postNABatFileListQueue,
  getNABatFileList,
} from "@api/NABatApi";
import { getProcessingTaskDetails } from "@api/api";

const POLL_INTERVAL_MS = 1000;

// `isStale` is checked both before issuing the next poll and right after it
// resolves, so a superseded call stops making requests immediately instead of
// polling to completion and merely having its result discarded - letting
// multiple abandoned loops pile up (and, under the dev server, exhaust the
// browser's small per-origin connection limit, queuing up new clicks behind
// them).
async function waitForTask(
  taskId: string,
  isStale: () => boolean,
  onProgress?: (description: string) => void,
): Promise<void> {
  while (!isStale()) {
    const details = await getProcessingTaskDetails(taskId);
    if (isStale()) {
      return;
    }
    if (details.celery_data.status === "Complete") {
      return;
    }
    if (details.celery_data.status === "Error") {
      throw new Error(details.celery_data.error || "Processing failed");
    }
    if (onProgress && details.celery_data.info?.description) {
      onProgress(details.celery_data.info.description as string);
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
  }
}

async function resolveRecordingId(
  fileListId: number,
  position: number,
): Promise<number> {
  const status = await getNABatFileList(fileListId);
  const item = status.items[position];
  if (!item?.nabatRecordingId) {
    throw new Error(
      `File list item at position ${position} did not materialize`,
    );
  }
  return item.nabatRecordingId;
}

export default function useNABatFileListQueue() {
  // Queues `position` (and its two neighbors) if needed, waits for `position`
  // itself to finish processing, and resolves with its local NABatRecording id -
  // what /nabat/:id/spectrogram actually takes. `isStale` lets the caller abandon
  // this mid-wait (e.g. the user clicked a different item) - once it reports true,
  // polling stops immediately and this throws rather than continuing to poll for
  // a result nothing will use. The caller already discards any error from a
  // superseded call via its own token check, so the exact error type doesn't
  // matter here.
  async function queuePositionAndWait(
    fileListId: number,
    position: number,
    isStale: () => boolean,
    onProgress?: (description: string) => void,
  ): Promise<number> {
    const response = await postNABatFileListQueue(fileListId, position);
    const taskId = response.queuedTaskIds[position.toString()];
    if (taskId) {
      await waitForTask(taskId, isStale, onProgress);
    }
    if (isStale()) {
      throw new Error("Superseded by a newer request");
    }
    return resolveRecordingId(fileListId, position);
  }

  // Same, but also creates the list (or re-verifies access to an existing one)
  // first - for the initial entrypoint, which always waits on position 0 and has
  // no "superseded by a later click" scenario, so there's no isStale to pass.
  async function createFileListAndWaitForFirst(
    fileListId: number,
    onProgress?: (description: string) => void,
  ): Promise<number> {
    const response = await postNABatFileListCreate(fileListId);
    const taskId = response.queuedTaskIds["0"];
    if (taskId) {
      await waitForTask(taskId, () => false, onProgress);
    }
    return resolveRecordingId(fileListId, 0);
  }

  return {
    queuePositionAndWait,
    createFileListAndWaitForFirst,
  };
}
