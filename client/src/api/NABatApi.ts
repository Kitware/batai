import { axiosInstance, FileAnnotation, ProcessingTask, Spectrogram } from "./api";

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

async function getSpectrogram(id: string) {
    return axiosInstance.get<Spectrogram>(`/nabat/recording/${id}/spectrogram`);
}

async function getSpectrogramCompressed(id: string) {
    return axiosInstance.get<Spectrogram>(`/nabat/recording/${id}/spectrogram/compressed`);

}

async function getNABatRecordingFileAnnotations(recordingId: number) {
    return axiosInstance.get<FileAnnotation[]>(`/nabat/recording/${recordingId}/recording-annotations`);
}



export {
    postNABatRecording,
    getSpectrogram,
    getSpectrogramCompressed,
    getNABatRecordingFileAnnotations,
};