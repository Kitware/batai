import {
  axiosInstance,
  type FileAnnotation,
  type FileAnnotationDetails,
  type ProcessingTask,
  type Spectrogram,
  type UpdateFileAnnotation,
  type Species,
  type ComputedPulseContour,
  type PulseMetadata,
} from "./api";

export interface NABatRecordingCompleteResponse {
  error?: string;
  taskId: string;
  status?: ProcessingTask["status"];
}

export interface NATBatFiles {
  id: number;
  recording_time: string;
  recording_location: string | null;
  file_name: string | null;
  s3_verified: boolean | null;
  length_ms: number | null;
  size_bytes: number | null;
  survey_event: null;
}

export interface NABatRecordingDataResponse {
  recordingId: string;
}
export type NABatRecordingResponse =
  NABatRecordingCompleteResponse | NABatRecordingDataResponse;

function isNABatRecordingCompleteResponse(
  response: NABatRecordingResponse,
): response is NABatRecordingCompleteResponse {
  return "taskId" in response;
}

async function postNABatAuth(
  recordingId: string,
  surveyEventId: string,
  iss: string,
  code: string,
) {
  const formData = new FormData();
  formData.append("iss", iss);
  formData.append("code", code);
  formData.append("recordingId", recordingId.toString());
  formData.append("surveyEventId", surveyEventId.toString());
  const response = await axiosInstance.post(
    "nabat/recording/authorize",
    formData,
  );
  return response.data;
}

async function postNABatRecording(recordingId: number, surveyEventId: number) {
  const formData = new FormData();
  formData.append("recordingId", recordingId.toString());
  formData.append("surveyEventId", surveyEventId.toString());
  const response = (
    await axiosInstance.post<NABatRecordingResponse>(
      "nabat/recording/",
      formData,
    )
  ).data;
  if (isNABatRecordingCompleteResponse(response)) {
    return response as NABatRecordingCompleteResponse;
  }
  return response as NABatRecordingDataResponse;
}

async function postNABatFileListAuth(
  fileListId: string,
  iss: string,
  code: string,
) {
  const formData = new FormData();
  formData.append("iss", iss);
  formData.append("code", code);
  formData.append("fileListId", fileListId.toString());
  const response = await axiosInstance.post(
    "nabat/file-list/authorize",
    formData,
  );
  return response.data;
}

export interface NABatFileListQueueResponse {
  fileListId: number;
  queuedTaskIds: Record<string, string>;
}

// Also queues position 0 and its two neighbors, same as postNABatFileListQueue -
// see _queue_positions on the backend, shared by both.
async function postNABatFileListCreate(fileListId: number) {
  const formData = new FormData();
  formData.append("fileListId", fileListId.toString());
  const response = await axiosInstance.post<NABatFileListQueueResponse>(
    "nabat/file-list/create",
    formData,
  );
  return response.data;
}

export type NABatFileListItemStatus =
  "exists" | "queued" | "failed" | "does_not_exist";

export interface NABatFileListItemInfo {
  id: number;
  recordingId: number;
  fileName: string | null;
  recordingTime: string | null;
  status: NABatFileListItemStatus;
  // The local NABatRecording id, once materialized - what /nabat/:id/spectrogram
  // actually takes. null until the item's status is "exists".
  nabatRecordingId: number | null;
}

export interface NABatFileListStatusResponse {
  fileListId: number;
  items: NABatFileListItemInfo[];
}

async function getNABatFileList(fileListId: number) {
  const response = await axiosInstance.get<NABatFileListStatusResponse>(
    `nabat/file-list/${fileListId}`,
  );
  return response.data;
}

// Queues `position` and its two neighbors (position + 1, position + 2) for
// materialization - see queue_nabat_file_list_items on the backend.
async function postNABatFileListQueue(fileListId: number, position: number) {
  const response = await axiosInstance.post<NABatFileListQueueResponse>(
    `nabat/file-list/${fileListId}/${position}`,
  );
  return response.data;
}

async function getNABatSpectrogram(id: string) {
  return axiosInstance.get<Spectrogram>(`nabat/recording/${id}/spectrogram`);
}

async function getNABatSpectrogramCompressed(id: string) {
  return axiosInstance.get<Spectrogram>(
    `nabat/recording/${id}/spectrogram/compressed`,
  );
}

async function getNABatRecordingFileAnnotations(recordingId: number) {
  return axiosInstance.get<FileAnnotation[]>(
    `nabat/recording/${recordingId}/recording-annotations`,
  );
}

async function getNABatFileAnnotations(recordingId: number) {
  return axiosInstance.get<FileAnnotation[]>(
    `recording/${recordingId}/recording-annotations`,
  );
}

async function getNABatSpecies({
  recordingId,
  grtsCellId,
  sampleFrameId,
}: {
  recordingId?: number;
  grtsCellId?: number;
  sampleFrameId?: number;
}) {
  return axiosInstance.get<Species[]>("/species/", {
    params: {
      recording_id: recordingId,
      grts_cell_id: grtsCellId,
      sample_frame_id: sampleFrameId,
      nabat: true,
    },
  });
}

async function getNABatFileAnnotationDetails(recordingId: number) {
  return axiosInstance.get<FileAnnotation & { details: FileAnnotationDetails }>(
    `nabat/recording/recording-annotation/${recordingId}/details`,
  );
}

async function putNABatFileAnnotation(fileAnnotation: UpdateFileAnnotation) {
  return axiosInstance.put<{ message: string; id: number }>(
    `nabat/recording/recording-annotation`,
    { ...fileAnnotation },
  );
}

// This function is used to patch a file annotation locally, without the NABat API.
async function patchNABatFileAnnotationLocal(
  fileAnnotationId: number,
  fileAnnotation: UpdateFileAnnotation,
) {
  return axiosInstance.patch<{ message: string; id: number }>(
    `nabat/recording/recording-annotation/${fileAnnotationId}`,
    { ...fileAnnotation },
  );
}

// This function is used to patch a file annotation with the NABat API.  Only takes a single species code in the array
async function pushNABatFileAnnotationToNABat(
  fileAnnotationId: number,
  fileAnnotation: UpdateFileAnnotation,
) {
  return axiosInstance.patch<{ message: string; id: number }>(
    `nabat/recording/recording-annotation/${fileAnnotationId}/push-to-nabat`,
    { ...fileAnnotation },
  );
}

async function deleteNABatFileAnnotation(
  fileAnnotationId: number,
  recordingId?: number,
) {
  return axiosInstance.delete<{ message: string; id: number }>(
    `nabat/recording/recording-annotation/${fileAnnotationId}`,
    { params: { recordingId } },
  );
}

export interface RecordingListItem {
  id: number;
  recording_id: number | null;
  survey_event_id: number | null;
  acoustic_batch_id: number | null;
  name: string;
  created: string | null;
  recording_location?: GeoJSON.Point | null;
  annotation_count: number | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  count: number;
  limit: number;
  offset: number;
}

export interface Annotation {
  id: number;
  comments: string | null;
  confidence: number | null;
  created: string;
  user_id: string | null;
  user_email: string | null;
  species: string[] | null;
  model: string | null;
}

export interface NABatStats {
  total_recordings: number;
  total_annotations: number;
}

export interface NABatConfigurationRecordingParams {
  survey_event_id?: number;
  recording_id?: number;
  bbox?: [number, number, number, number];
  location?: [number, number];
  sort_by?: "created" | "recording_id" | "survey_event_id" | "annotation_count";
  sort_direction?: "asc" | "desc";
  radius?: number;
  page?: number;
  limit?: number;
  offset?: number;
}

// Function to get paginated recordings with filters
async function getNABatConfigurationRecordings(
  filters: NABatConfigurationRecordingParams,
) {
  const response = await axiosInstance.get<
    PaginatedResponse<RecordingListItem>
  >("/nabat/configuration/recordings", {
    params: filters,
  });
  return response.data;
}

export interface NABatConfigurationAnnotationFilterParams {
  page?: number;
  limit?: number;
  offset?: number;
  sort_by?: "created" | "user_email" | "confidence";
  sort_direction?: "asc" | "desc";
}

// Function to get paginated annotations for a recording
async function getNABatConfigurationAnnotations(
  recordingId: number,
  filters?: NABatConfigurationAnnotationFilterParams,
) {
  const response = await axiosInstance.get<PaginatedResponse<Annotation>>(
    `/nabat/configuration/recordings/${recordingId}/annotations`,
    {
      params: filters,
    },
  );
  return response.data;
}

async function getNABatConfigurationStats(): Promise<NABatStats> {
  const response = await axiosInstance.get<NABatStats>(
    "/nabat/configuration/stats",
  );
  return response.data;
}

export interface AnnotationExportRequest {
  start_date?: string; // ISO date string (e.g., "2025-05-30")
  end_date?: string;
  recording_ids?: number[];
  usernames?: string[];
  min_confidence?: number;
  max_confidence?: number;
}

export interface AnnotationExportResponse {
  exportId: number;
}

async function adminNaBatUpdateSpecies(apiToken: string) {
  return axiosInstance.post<{ taskId: string }>(
    "/nabat/configuration/update-species",
    {
      params: { apiToken },
    },
  );
}

async function exportNABatAnnotations(
  filters: AnnotationExportRequest,
): Promise<AnnotationExportResponse> {
  const response = await axiosInstance.post<AnnotationExportResponse>(
    "nabat/configuration/export",
    filters,
  );
  return response.data;
}

async function getNabatPulseContours(recordingId: string) {
  const result = await axiosInstance.get<ComputedPulseContour[]>(
    `nabat/recording/${recordingId}/pulse_contours`,
  );
  return result.data;
}

async function getNabatPulseMetadata(recordingId: string) {
  const result = await axiosInstance.get<PulseMetadata[]>(
    `nabat/recording/${recordingId}/pulse_metadata`,
  );
  return result.data;
}

export {
  postNABatAuth,
  postNABatRecording,
  postNABatFileListAuth,
  postNABatFileListCreate,
  getNABatFileList,
  postNABatFileListQueue,
  getNABatSpectrogram,
  getNABatSpectrogramCompressed,
  getNABatRecordingFileAnnotations,
  getNABatFileAnnotations,
  getNABatSpecies,
  getNABatFileAnnotationDetails,
  putNABatFileAnnotation,
  patchNABatFileAnnotationLocal,
  pushNABatFileAnnotationToNABat,
  deleteNABatFileAnnotation,
  getNABatConfigurationStats,
  getNABatConfigurationAnnotations,
  getNABatConfigurationRecordings,
  exportNABatAnnotations,
  adminNaBatUpdateSpecies,
  getNabatPulseContours,
  getNabatPulseMetadata,
};
