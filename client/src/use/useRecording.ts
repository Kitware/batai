import { getRecording, Recording } from "@api/api";
import { ref, Ref } from "vue";

const recordingInfo: Ref<Recording | null> = ref(null);
let recordingRequestCounter = 0;

export default function useRecording() {
  async function updateRecordingInfo(id: string) {
    recordingInfo.value = null;

    recordingRequestCounter += 1;
    const currentRequestId = recordingRequestCounter;
    const recording = await getRecording(id);

    if (recordingRequestCounter === currentRequestId) {
      // Only set the data if `recordingRequestCounter` hasn't changed
      // since initiating the request.
      recordingInfo.value = recording.data;
    }
  }

  function clearRecordingInfo() {
    recordingInfo.value = null;
  }

  return {
    recordingInfo,
    updateRecordingInfo,
    clearRecordingInfo,
  };
}
