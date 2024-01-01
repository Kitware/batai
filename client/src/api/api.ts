import axios from 'axios';
import { GeoJsonObject } from 'geojson';
import { createS3ffClient } from '../plugins/S3FileField';
import { S3FileFieldProgressCallback } from 'django-s3-file-field';

export interface PaginatedResponse<E> {
    count: number,
    next: string,
    previous:string,
    results: E[];
}

export interface Recording {
    id: number,
    created: string,
    modified: string,
    name: string,
    audio_file: string,
    audio_file_presigned_url: string,
    owner_id: number;
    owner_username: string;
    recorded_date: string;
    equipment?: string,
    comments?: string;
    recording_location?: null | [number, number],
    grts_cell_id?: null | number;
    grts_cell?: null | number;
}

export interface AcousticFiles {
    id: number,
    recording_time: string;
    recording_location: string | null;
    file_name: string | null;
    s3_verified: boolean | null;
    length_ms: number | null;
    size_bytes: number | null;
    survey_event: null;
}

export interface Species {
    species_code: string;
    family: string;
    genus: string;
    common_name: string;
    species_code_6?: string;
}

export interface SpeciesBatch {
    species: string,

}

export interface SpectrogramAnnotation {
    offset: number,
    frequency: number,
}

export interface SpectrogramBatches {
    vetter: string | null;
    auto?: Species;
    manual?: Species;
}

export interface Spectrogram {
    url: string;
    filename: string;
    project: number;
    annotations?: SpectrogramAnnotation[];
    batches?: SpectrogramBatches[];
    images: string[];

}

interface PaginatedNinjaResponse<T> {
    count: number,
    items: T[],
}

export interface Project {
    projectKey: string;
    name: string;
    description: string;
    grtsIds: number[];
    grtsCellIds: number[];
    surveyUUID: string[];
    eventGeometryName: string[];
    eventGeometryDesc: string[];
    eventGeometryGeom: GeoJsonObject;
    surveys: number;
}

export interface Survey {
    id: number;
    startTime: Date;
    endTime: Date;
    createdDate: Date;
    modifiedDate: Date;
    uuid: string;
    eventGeom: GeoJsonObject;
    createdBy: string;
    modifiedBy: string;
    fileCount: number;
    surveyTypeDesc?: string;
    surveyMapColor?: string;

}

export interface SurveyDetails {
    id: string;
    batchId: number;
    fileId: number;
    fileName: string;
    auto?: Species;
    manual?: Species;
    software?: {
        name?: string;
        developer?: string;
        version?: string;
    };
    classifier: {
        name?: string;
        description?: string;
        public?: boolean;
    }
    annotationCount: number;

}


export const axiosInstance = axios.create({
  baseURL: import.meta.env.VUE_APP_API_ROOT as string,
});


async function uploadRecordingFile(file: File, name: string, recorded_date: string, equipment: string, comments: string ) {
    const formData = new FormData();
    formData.append('audio_file', file);
    formData.append('name', name);
    formData.append('recorded_date', recorded_date);
    formData.append('equipment', equipment);
    formData.append('comments', comments);
    
    const recordingParams = {
      name,
      equipment,
      comments
    };
    const payloadBlob = new Blob([JSON.stringify(recordingParams)], { type: 'application/json' });
    formData.append('payload', payloadBlob);
  await axiosInstance.post('/recording/',
    formData,
    { 
        headers: {
            'Content-Type': 'multipart/form-data',   
        }
     });
  }
  
async function getRecordings() {
    return axiosInstance.get<Recording[]>('/recording/');
}


export {
 uploadRecordingFile,
 getRecordings,
};