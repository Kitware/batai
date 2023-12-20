import axios from 'axios';
import { GeoJsonObject } from 'geojson';
export interface PaginatedResponse<E> {
    count: number,
    next: string,
    previous:string,
    results: E[];
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


async function getAcousticFiles(offset=0, limit=-1) {
  const data = (await axiosInstance.get<PaginatedResponse<AcousticFiles>>(`/acoustic_file?offset=${offset}&limit=${limit}`)).data;
  return data;
}

async function getAcoustFilesS3Exists(offset=0, limit=-1) {
    const data = (await axiosInstance.get<PaginatedResponse<AcousticFiles>>(`/acoustic_file/s3_exists?offset=${offset}&limit=${limit}`)).data;
    return data;
  
}

async function getSpecies(offset=0, limit=-1) {
    const data = (await axiosInstance.get<PaginatedResponse<Species>>(`/species/?offset=${offset}&limit=${limit}`)).data;
    return data;

}

async function getSpectrogram(id: string, offset=0, limit=-1) {
    const data = (await axiosInstance.get<Spectrogram>(`/spectrogram/${id}?offset=${offset}&limit=${limit}`)).data;
    return data;

}

async function getProjects(offset=0, limit=100) {
    const data = (await axiosInstance.get<PaginatedNinjaResponse<Project>>(`/project/?offset=${offset}&limit=${limit}`)).data;
    return data;

}

async function getProject(projectKey: string, offset=0, limit=100) {
    const data = (await axiosInstance.get<PaginatedNinjaResponse<Survey>>(`/project/${projectKey}?offset=${offset}&limit=${limit}`)).data;
    return data;

}


async function getSurveys(offset=0, limit=100) {
    const data = (await axiosInstance.get<PaginatedNinjaResponse<Survey>>(`/survey/?offset=${offset}&limit=${limit}`)).data;
    return data;

}

async function getSurvey(uuid: string, offset=0, limit=100) {
    const data = (await axiosInstance.get<PaginatedNinjaResponse<SurveyDetails>>(`/survey/${uuid}?offset=${offset}&limit=${limit}`)).data;
    return data;

}



export {
 getAcousticFiles,
 getAcoustFilesS3Exists,
 getSpecies,
 getSpectrogram,
 getProjects,
 getProject,
 getSurveys,
 getSurvey
};