import { axiosInstance, FileAnnotation, FileAnnotationDetails, ProcessingTask, Spectrogram, UpdateFileAnnotation } from "./api";

export interface NABatRecordingCompleteResponse {
    error?: string;
    taskId: string;
    status?: ProcessingTask['status'];
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

async function getSpectrogram(id: string, apiToken: string) {
    return axiosInstance.get<Spectrogram>(`/nabat/recording/${id}/spectrogram?apiToken=${apiToken}`);
}

async function getSpectrogramCompressed(id: string, apiToken: string) {
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



export {
    postNABatRecording,
    getSpectrogram,
    getSpectrogramCompressed,
    getNABatRecordingFileAnnotations,
    getNABatFileAnnotations,
    getNABatFileAnnotationDetails,
    putNABatFileAnnotation,
    patchNABatFileAnnotation,
    deleteNABatFileAnnotation
};