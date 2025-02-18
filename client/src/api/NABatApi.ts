import { axiosInstance, ProcessingTask, Spectrogram } from "./api";

export interface AcousticBatchCompleteResponse {
    error?: string;
    taskId: string;
    status?: ProcessingTask['status'];
}
export type AcousticBatchResponse = AcousticBatchCompleteResponse | Spectrogram;

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
    return response as Spectrogram;
}


export {
    postAcousticBatch,
};