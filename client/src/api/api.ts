import axios from "axios";
import { SpectroInfo } from "@components/geoJS/geoJSUtils";

export interface Recording {
  id: number;
  created: string;
  modified: string;
  name: string;
  audio_file: string;
  audio_file_presigned_url: string;
  owner_id: number;
  owner_username: string;
  recorded_date: string;
  recorded_time: string;
  equipment?: string;
  comments?: string;
  recording_location?: null | GeoJSON.Point;
  grts_cell_id?: null | number;
  grts_cell?: null | number;
  public: boolean;
  userMadeAnnotations: boolean;
  userAnnotations: number;
  hasSpectrogram: boolean;
  fileAnnotations: FileAnnotation[];
  site_name?: string;
  software?: string;
  detector?: string;
  species_list?: string;
  unusual_occurrences?: string;
  tags_text?: string[];
}

export interface Species {
  species_code: string;
  family: string;
  genus: string;
  common_name: string;
  species_code_6?: string;
  id: number;
  category: "individual" | "couplet" | "frequency" | "noid";
}

export interface SpectrogramAnnotation {
  start_time: number;
  end_time: number;
  low_freq: number;
  high_freq: number;
  id: number;
  editing?: boolean;
  species?: Species[];
  comments?: string;
  type?: string;
  owner_email?: string;
}

export interface SpectrogramSequenceAnnotation {
  start_time: number;
  end_time: number;
  id: number;
  editing?: boolean;
  type?: string;
  comments?: string;
  species?: Species[];
  owner_email?: string;
}

export interface UpdateSpectrogramAnnotation {
  start_time?: number;
  end_time?: number;
  low_freq?: number;
  high_freq?: number;
  id?: number;
  editing?: boolean;
  type?: string;
  species?: Species[];
  comments?: string;
}

export interface UpdateSpectrogramSequenceAnnotation {
  start_time?: number;
  end_time?: number;
  id?: number;
  editing?: boolean;
  species?: Species[];
  comments?: string;
  type?: string;
}

export interface UserInfo {
  username: string;
  email: string;
  id: number;
}

export interface FileAnnotation {
  species: Species[];
  comments?: string;
  model?: string;
  owner: string;
  confidence: number;
  hasDetails: boolean;
  id: number;
  submitted: boolean;
}

export interface FileAnnotationDetails {
  label: string;
  score: number;
  confidences: { label: string; value: string }[];
}
export interface UpdateFileAnnotation {
  recordingId?: number;
  species: number[] | null;
  comments?: string;
  model?: string;
  confidence: number;
  id?: number;
}

export interface Spectrogram {
  urls: string[];
  filename?: string;
  annotations?: SpectrogramAnnotation[];
  fileAnnotations: FileAnnotation[];
  sequence?: SpectrogramSequenceAnnotation[];
  spectroInfo?: SpectroInfo;
  compressed?: {
    start_times: number[];
    end_times: number[];
  };
  currentUser?: string;
  otherUsers?: UserInfo[];
}

export type OtherUserAnnotations = Record<
  string,
  { annotations: SpectrogramAnnotation[]; sequence: SpectrogramSequenceAnnotation[] }
>;

export type UploadLocation = null | { latitude?: number; longitude?: number; gridCellId?: number };

export const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_APP_API_ROOT as string,
});

export interface RecordingFileParameters {
  name: string;
  recorded_date: string;
  recorded_time: string;
  equipment: string;
  comments: string;
  location?: UploadLocation;
  publicVal: boolean;
  site_name?: string;
  software?: string;
  detector?: string;
  species_list?: string;
  unusual_occurrences?: string;
  tags?: string[];
}

async function uploadRecordingFile(file: File, params: RecordingFileParameters) {
  const formData = new FormData();
  formData.append("audio_file", file);
  formData.append("name", params.name);
  formData.append("recorded_date", params.recorded_date);
  formData.append("recorded_time", params.recorded_time);
  formData.append("equipment", params.equipment);
  formData.append("comments", params.comments);
  if (params.location) {
    if (params.location.latitude && params.location.longitude) {
      formData.append("latitude", params.location.latitude.toString());
      formData.append("longitude", params.location.longitude.toString());
    }
    if (params.location.gridCellId) {
      formData.append("gridCellId", params.location.gridCellId.toString());
    }
  }

  if (params.software) {
    formData.append("software", params.software);
  }
  if (params.detector) {
    formData.append("detector", params.detector);
  }
  if (params.site_name) {
    formData.append("site_name", params.site_name);
  }
  if (params.species_list) {
    formData.append("species_list", params.species_list);
  }
  if (params.unusual_occurrences) {
    formData.append("unusual_occurrences", params.unusual_occurrences);
  }
  if (params.tags) {
    params.tags.forEach((tag: string) => formData.append("tags", tag));
  }
  const recordingParams = {
    name: params.name,
    equipment: params.equipment,
    comments: params.comments,
    site_name: params.site_name,
    software: params.software,
    detector: params.detector,
    species_list: params.species_list,
    unusual_occurrences: params.unusual_occurrences,
    tags: params.tags,
  };
  const payloadBlob = new Blob([JSON.stringify(recordingParams)], { type: "application/json" });
  formData.append("payload", payloadBlob);
  await axiosInstance.post("/recording/", formData, {
    params: { publicVal: !!params.publicVal },
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
}

async function patchRecording(recordingId: number, params: RecordingFileParameters) {
  const latitude = params.location ? params.location.latitude : undefined;
  const longitude = params.location ? params.location.longitude : undefined;
  const gridCellId = params.location ? params.location.gridCellId : undefined;

  await axiosInstance.patch(
    `/recording/${recordingId}`,
    {
      name: params.name,
      recorded_date: params.recorded_date,
      recorded_time: params.recorded_time,
      equipment: params.equipment,
      comments: params.comments,
      publicVal: !!params.publicVal,
      latitude,
      longitude,
      gridCellId,
      tags: params.tags,
      site_name: params.site_name,
      software: params.software,
      detector: params.detector,
      species_list: params.species_list,
      unusual_occurrences: params.unusual_occurrences,
    },
    {
      headers: {
        "Content-Type": "application/json",
      },
    }
  );
}

interface DeletionResponse {
  message?: string;
  error?: string;
}
interface GRTSCellCenter {
  latitude?: number;
  longitude?: number;
  error?: string;
}

export interface RecordingTag {
  id: number;
  text: string;
  user_id: number;
}

async function getRecordings(getPublic = false) {
  return axiosInstance.get<Recording[]>(`/recording/?public=${getPublic}`);
}
async function getRecording(id: string) {
  return axiosInstance.get<Recording>(`/recording/${id}/`);
}
async function getRecordingTags() {
  return axiosInstance.get<RecordingTag[]>(`/recording-tag/`);
}

async function deleteRecording(id: number) {
  return axiosInstance.delete<DeletionResponse>(`/recording/${id}`);
}

async function getSpectrogram(id: string) {
  return axiosInstance.get<Spectrogram>(`/recording/${id}/spectrogram`);
}

async function getSpectrogramCompressed(id: string) {
  return axiosInstance.get<Spectrogram>(`/recording/${id}/spectrogram/compressed`);
}

async function getAnnotations(recordingId: string) {
  return axiosInstance.get<SpectrogramAnnotation[]>(`/recording/${recordingId}/annotations`);
}

async function getSequenceAnnotations(recordingId: string) {
  return axiosInstance.get<SpectrogramSequenceAnnotation[]>(
    `/recording/${recordingId}/sequence-annotations`
  );
}

async function getSpecies() {
  return axiosInstance.get<Species[]>("/species/");
}

async function patchAnnotation(
  recordingId: string,
  annotationId: number,
  annotation: UpdateSpectrogramAnnotation,
  speciesList: number[] | null = null
) {
  return axiosInstance.patch(`/recording/${recordingId}/annotations/${annotationId}`, {
    annotation,
    species_ids: speciesList,
  });
}

async function patchSequenceAnnotation(
  recordingId: string,
  annotationId: number,
  annotation: UpdateSpectrogramSequenceAnnotation,
  speciesList: number[] | null = null
) {
  return axiosInstance.patch(`/recording/${recordingId}/sequence-annotations/${annotationId}`, {
    annotation,
    species_ids: speciesList,
  });
}

async function putAnnotation(
  recordingId: string,
  annotation: UpdateSpectrogramAnnotation,
  speciesList: number[] = []
) {
  return axiosInstance.put<{ message: string; id: number }>(
    `/recording/${recordingId}/annotations`,
    { annotation, species_ids: speciesList }
  );
}

async function putSequenceAnnotation(
  recordingId: string,
  annotation: UpdateSpectrogramSequenceAnnotation,
  speciesList: number[] | null = null
) {
  return axiosInstance.put<{ message: string; id: number }>(
    `/recording/${recordingId}/sequence-annotations`,
    { annotation, species_ids: speciesList }
  );
}

async function deleteAnnotation(recordingId: string, annotationId: number) {
  return axiosInstance.delete<DeletionResponse>(
    `/recording/${recordingId}/annotations/${annotationId}`
  );
}

async function deleteSequenceAnnotation(recordingId: string, annotationId: number) {
  return axiosInstance.delete<DeletionResponse>(
    `/recording/${recordingId}/sequence-annotations/${annotationId}`
  );
}

async function getOtherUserAnnotations(recordingId: string) {
  return axiosInstance.get<OtherUserAnnotations>(
    `/recording/${recordingId}/annotations/other_users`
  );
}

async function getCellLocation(cellId: number, quadrant?: "SW" | "NE" | "NW" | "SE") {
  return axiosInstance.get<GRTSCellCenter>(`/grts/${cellId}`, { params: { quadrant } });
}
async function getFileAnnotations(recordingId: number) {
  return axiosInstance.get<FileAnnotation[]>(`recording/${recordingId}/recording-annotations`);
}

async function getFileAnnotationDetails(recordingId: number) {
  return axiosInstance.get<FileAnnotation & { details: FileAnnotationDetails }>(
    `recording-annotation/${recordingId}/details`
  );
}

async function putFileAnnotation(fileAnnotation: UpdateFileAnnotation) {
  return axiosInstance.put<{ message: string; id: number }>(`/recording-annotation/`, {
    ...fileAnnotation,
  });
}

async function patchFileAnnotation(fileAnnotationId: number, fileAnnotation: UpdateFileAnnotation) {
  return axiosInstance.patch<{ message: string; id: number }>(
    `/recording-annotation/${fileAnnotationId}`,
    { ...fileAnnotation }
  );
}

async function deleteFileAnnotation(fileAnnotationId: number) {
  return axiosInstance.delete<{ message: string; id: number }>(
    `/recording-annotation/${fileAnnotationId}`
  );
}

interface CellIDReponse {
  grid_cell_id?: number;
  error?: string;
}
async function getCellfromLocation(latitude: number, longitude: number) {
  return axiosInstance.get<CellIDReponse>(`/grts/grid_cell_id`, {
    params: { latitude, longitude },
  });
}

export interface ConfigurationSettings {
  display_pulse_annotations: boolean;
  display_sequence_annotations: boolean;
  run_inference_on_upload: boolean;
  spectrogram_x_stretch: number;
  spectrogram_view: "compressed" | "uncompressed";
  is_admin?: boolean;
  default_color_scheme: string;
  default_spectrogram_background_color: string;
  non_admin_upload_enabled: boolean;
  mark_annotations_completed_enabled: boolean;
  show_my_recordings: boolean;
}

export type Configuration = ConfigurationSettings & { is_admin: boolean };
async function getConfiguration() {
  return axiosInstance.get<Configuration>("/configuration/");
}

async function patchConfiguration(config: ConfigurationSettings) {
  return axiosInstance.patch("/configuration/", { ...config });
}

async function getCurrentUser() {
  return axiosInstance.get<{name: string, email: string}>("/configuration/me");
}

export interface ProcessingTask {
  id: number;
  created: string;
  modified: string;
  name: string;
  file_items: number[];
  error?: string;
  info?: string;
  status: "Complete" | "Running" | "Error" | "Queued";
  metadata: Record<string, unknown> & { type?: "NABatRecordingProcessing" } & {
    recordingId: string;
  };
  output_metadata: Record<string, unknown>;
}
export interface ProcessingTaskDetails {
  name: string;
  celery_data: {
    state: "PENDING" | "RECEIVED" | "STARTED" | "SUCCESS" | "FAILURE" | "RETRY" | "REVOKED";
    status: ProcessingTask["status"];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    info: Record<string, any>;
    error: string;
  };
}

async function getProcessingTasks(): Promise<ProcessingTask[]> {
  return (await axiosInstance.get("/processing-task")).data;
}

async function getProcessingTaskDetails(taskId: string): Promise<ProcessingTaskDetails> {
  return (await axiosInstance.get(`/processing-task/${taskId}/details`)).data;
}

async function getFilteredProcessingTasks(
  status: ProcessingTask["status"]
): Promise<ProcessingTask[]> {
  return (await axiosInstance.get("/processing-task/filtered/", { params: { status } })).data;
}

async function cancelProcessingTask(taskId: number): Promise<{ detail: string }> {
  return (await axiosInstance.post(`/processing-task/${taskId}/cancel/`)).data;
}

interface GuanoMetadata {
  nabat_grid_cell_grts_id?: string;
  nabat_latitude?: number;
  nabat_longitude?: number;
  nabat_site_name?: string;
  nabat_activation_start_time?: string;
  nabat_activation_end_time?: string;
  nabat_software_type?: string;
  nabat_species_list?: string[];
  nabat_comments?: string;
  nabat_detector_type?: string;
  nabat_unusual_occurrences?: string;
}

async function getGuanoMetadata(file: File): Promise<GuanoMetadata> {
  const formData = new FormData();
  formData.append("audio_file", file);
  const results = await axiosInstance.post<GuanoMetadata>("/guano/", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return results.data;
}

export interface ExportStatus {
  id: number;
  status: "pending" | "complete" | "failed";
  downloadUrl?: string;
  created: string;
  expiresAt: string;
}

async function getExportStatus(exportId: number) {
  const result = await axiosInstance.get<ExportStatus>(`/export-annotation/${exportId}`);
  return result.data;
}

export {
  uploadRecordingFile,
  getRecordings,
  getRecording,
  patchRecording,
  deleteRecording,
  getSpectrogram,
  getSpectrogramCompressed,
  getSequenceAnnotations,
  getOtherUserAnnotations,
  getSpecies,
  getAnnotations,
  patchAnnotation,
  patchSequenceAnnotation,
  putAnnotation,
  putSequenceAnnotation,
  deleteAnnotation,
  deleteSequenceAnnotation,
  getCellLocation,
  getCellfromLocation,
  getGuanoMetadata,
  getFileAnnotations,
  putFileAnnotation,
  patchFileAnnotation,
  deleteFileAnnotation,
  getConfiguration,
  patchConfiguration,
  getProcessingTasks,
  getProcessingTaskDetails,
  cancelProcessingTask,
  getFilteredProcessingTasks,
  getFileAnnotationDetails,
  getExportStatus,
  getRecordingTags,
  getCurrentUser,
};
