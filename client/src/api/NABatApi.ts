import { axiosInstance, FileAnnotation, FileAnnotationDetails, ProcessingTask, Spectrogram, UpdateFileAnnotation } from "./api";

export interface NABatRecordingCompleteResponse {
    error?: string;
    taskId: string;
    status?: ProcessingTask['status'];
}

export interface NATBatFiles {
    id: number,
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
export type NABatRecordingResponse = NABatRecordingCompleteResponse | NABatRecordingDataResponse;

function isNABatRecordingCompleteResponse(response: NABatRecordingResponse): response is NABatRecordingCompleteResponse {
    return "taskId" in response;
}

async function postNABatRecording(recordingId: number, surveyEventId: number, apiToken: string) {
    const formData = new FormData();
    formData.append('recordingId', recordingId.toString());
    formData.append('apiToken', apiToken);
    formData.append('surveyEventId', surveyEventId.toString());
    const response =  (await (axiosInstance.post<NABatRecordingResponse>('/nabat/recording/', formData))).data;
    if (isNABatRecordingCompleteResponse(response)) {
        return response as NABatRecordingCompleteResponse;
    }
    return response as NABatRecordingDataResponse;
}

async function getNABatSpectrogram(id: string, apiToken: string) {
    return axiosInstance.get<Spectrogram>(`/nabat/recording/${id}/spectrogram?apiToken=${apiToken}`);
}

async function getNABatSpectrogramCompressed(id: string, apiToken: string) {
    return axiosInstance.get<Spectrogram>(`/nabat/recording/${id}/spectrogram/compressed?apiToken=${apiToken}`);

}

async function getNABatRecordingFileAnnotations(recordingId: number, apiToken?: string) {
    return axiosInstance.get<FileAnnotation[]>(`/nabat/recording/${recordingId}/recording-annotations`, { params: { apiToken } });
}


async function getNABatFileAnnotations(recordingId: number) {
  return axiosInstance.get<FileAnnotation[]>(`recording/${recordingId}/recording-annotations`);
}

async function getNABatFileAnnotationDetails(recordingId: number, apiToken?: string) {
    return axiosInstance.get<(FileAnnotation & {details: FileAnnotationDetails })>(`nabat/recording/recording-annotation/${recordingId}/details`, { params: { apiToken } });
}

async function putNABatFileAnnotation(fileAnnotation: UpdateFileAnnotation & { apiToken?: string}) {
  return axiosInstance.put<{ message: string, id: number }>(`nabat/recording/recording-annotation`, { ...fileAnnotation });
}

async function patchNABatFileAnnotation(fileAnnotationId: number, fileAnnotation: UpdateFileAnnotation & { apiToken?: string}) {
  return axiosInstance.patch<{ message: string, id: number }>(`nabat/recording/recording-annotation/${fileAnnotationId}`, { ...fileAnnotation });
}

async function deleteNABatFileAnnotation(fileAnnotationId: number, apiToken?: string) {
  return axiosInstance.delete<{ message: string, id: number }>(`nabat/recording/recording-annotation/${fileAnnotationId}`, { params: { apiToken } });
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
    sort_by?: 'created' | 'recording_id' | 'survey_event_id' | 'annotation_count';
    sort_direction?: 'asc' | 'desc';
    radius?: number;
    page?: number;
    limit?: number;
    offset?: number;
  }
  
  // Function to get paginated recordings with filters
  async function getNABatConfigurationRecordings(filters: NABatConfigurationRecordingParams) {
    const response = await axiosInstance.get<PaginatedResponse<RecordingListItem>>('/nabat/configuration/recordings', {
      params: filters,
    });
    return response.data;

  }

  export interface NABatConfigurationAnnotationFilterParams {
    page?: number;
    limit?: number;
    offset?: number;
    sort_by?: 'created' | 'user_email' | 'confidence';
    sort_direction?: 'asc' | 'desc';
  }

  // Function to get paginated annotations for a recording
  async function getNABatConfigurationAnnotations(
    recordingId: number,
    filters?: NABatConfigurationAnnotationFilterParams,
  ) {
    const response = await axiosInstance.get<PaginatedResponse<Annotation>>(`/nabat/configuration/recordings/${recordingId}/annotations`, {
      params: filters,
    });
    return response.data;
  }


async function getNABatConfigurationStats(): Promise<NABatStats> {
  const response = await axiosInstance.get<NABatStats>('/nabat/configuration/stats');
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

async function exportNABatAnnotations(filters: AnnotationExportRequest): Promise<AnnotationExportResponse> {
  const response = await axiosInstance.post<AnnotationExportResponse>('nabat/configuration/export', filters);
  return response.data;
}

export {
    postNABatRecording,
    getNABatSpectrogram,
    getNABatSpectrogramCompressed,
    getNABatRecordingFileAnnotations,
    getNABatFileAnnotations,
    getNABatFileAnnotationDetails,
    putNABatFileAnnotation,
    patchNABatFileAnnotation,
    deleteNABatFileAnnotation,
    getNABatConfigurationStats,
    getNABatConfigurationAnnotations,
    getNABatConfigurationRecordings,
    exportNABatAnnotations

};