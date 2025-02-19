import { axiosInstance, FileAnnotation, ProcessingTask, Spectrogram } from "./api";

export interface AcousticBatchCompleteResponse {
    error?: string;
    taskId: string;
    status?: ProcessingTask['status'];
}

export interface AcousticBatchDataResponse {
    acousticId: string;
}
export type AcousticBatchResponse = AcousticBatchCompleteResponse | AcousticBatchDataResponse;

function isAcousticBatchCompleteResponse(response: AcousticBatchResponse): response is AcousticBatchCompleteResponse {
    return "taskId" in response;
}

async function postAcousticBatch(batchId: number, apiToken: string) {
    const formData = new FormData();
    formData.append('batchId', batchId.toString());
    formData.append('apiToken', apiToken);
    const response =  (await (axiosInstance.post<AcousticBatchResponse>('/nabat/acoustic-batch/', formData))).data;
    if (isAcousticBatchCompleteResponse(response)) {
        return response as AcousticBatchCompleteResponse;
    }
    return response as AcousticBatchDataResponse;
}

async function getSpectrogram(id: string) {
    return axiosInstance.get<Spectrogram>(`/nabat/acoustic-batch/${id}/spectrogram`);
}

async function getSpectrogramCompressed(id: string) {
    return axiosInstance.get<Spectrogram>(`/nabat/acoustic-batch/${id}/spectrogram/compressed`);

}

async function getAcousticFileAnnotations(batchId: number) {
    return axiosInstance.get<FileAnnotation[]>(`/nabat/acoustic-batch/${batchId}/recording-annotations`);
}



export {
    postAcousticBatch,
    getSpectrogram,
    getSpectrogramCompressed,
    getAcousticFileAnnotations,
};