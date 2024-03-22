import axios from 'axios';
import { SpectroInfo } from '../components/geoJS/geoJSUtils';

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
    recorded_time: string;
    equipment?: string,
    comments?: string;
    recording_location?: null | GeoJSON.Point,
    grts_cell_id?: null | number;
    grts_cell?: null | number;
    public: boolean;
    userMadeAnnotations: boolean;
    userAnnotations: number;
    hasSpectrogram: boolean;
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
    id: number;
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

export interface SpectrogramTemporalAnnotation {
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

export interface UpdateSpectrogramTemporalAnnotation {
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
export interface Spectrogram {
    'base64_spectrogram': string;
    url?: string;
    filename?: string;
    annotations?: SpectrogramAnnotation[];
    temporal?: SpectrogramTemporalAnnotation[];
    spectroInfo?: SpectroInfo;
    currentUser?: string;
    otherUsers?: UserInfo[];

}

export type OtherUserAnnotations = Record<string, {annotations: SpectrogramAnnotation[], temporal: SpectrogramTemporalAnnotation[]}>;

interface PaginatedNinjaResponse<T> {
    count: number,
    items: T[],
}

export type UploadLocation =  null | { latitude?: number, longitude?: number, gridCellId?: number};

export const axiosInstance = axios.create({
  baseURL: import.meta.env.VUE_APP_API_ROOT as string,
});


async function uploadRecordingFile(file: File, name: string, recorded_date: string, recorded_time: string, equipment: string, comments: string, publicVal = false, location: UploadLocation = null ) {
    const formData = new FormData();
    formData.append('audio_file', file);
    formData.append('name', name);
    formData.append('recorded_date', recorded_date);
    formData.append('recorded_time', recorded_time);
    formData.append('equipment', equipment);
    formData.append('comments', comments);
    if (location) {
        if (location.latitude && location.longitude) {
            formData.append('latitude', location.latitude.toString());
            formData.append('longitude', location.longitude.toString());
        }
        if (location.gridCellId) {
            formData.append('gridCellId', location.gridCellId.toString());
        }
    }
    
    const recordingParams = {
      name,
      equipment,
      comments,
    };
    const payloadBlob = new Blob([JSON.stringify(recordingParams)], { type: 'application/json' });
    formData.append('payload', payloadBlob);
  await axiosInstance.post('/recording/',
    formData,
    { 
        params: { publicVal }, 
        headers: {
            'Content-Type': 'multipart/form-data',   
        }
     });
  }

  async function patchRecording(recordingId: number, name: string, recorded_date: string, recorded_time: string, equipment: string, comments: string, publicVal = false, location: UploadLocation = null ) {
    const latitude = location ? location.latitude : undefined;
    const longitude = location ? location.longitude : undefined;
    const gridCellId = location ? location.gridCellId : undefined;

    await axiosInstance.patch(`/recording/${recordingId}`, 
        { 
            name, 
            recorded_date, 
            recorded_time, 
            equipment, 
            comments, 
            publicVal, 
            latitude,
            longitude,
            gridCellId
        },
        {
            headers: {
                'Content-Type': 'application/json',
            }
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
  
async function getRecordings(getPublic=false) {
    return axiosInstance.get<Recording[]>(`/recording/?public=${getPublic}`);
}
async function getRecording(id: string) {
    return axiosInstance.get<Recording>(`/recording/${id}/`);
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

async function getTemporalAnnotations(recordingId: string) {
    return axiosInstance.get<SpectrogramTemporalAnnotation[]>(`/recording/${recordingId}/temporal-annotations`);
}

async function getSpecies() {
    return axiosInstance.get<Species[]>('/species/');
}

async function patchAnnotation(recordingId: string, annotationId: number, annotation: UpdateSpectrogramAnnotation, speciesList: number[] | null = null) {
    return axiosInstance.patch(`/recording/${recordingId}/annotations/${annotationId}`, { annotation, species_ids: speciesList});
}

async function patchTemporalAnnotation(recordingId: string, annotationId: number, annotation: UpdateSpectrogramTemporalAnnotation, speciesList: number[] | null = null) {
    return axiosInstance.patch(`/recording/${recordingId}/temporal-annotations/${annotationId}`, { annotation, species_ids: speciesList});
}

async function putAnnotation(recordingId: string, annotation: UpdateSpectrogramAnnotation, speciesList: number[] = []) {
    return axiosInstance.put<{message: string, id: number}>(`/recording/${recordingId}/annotations`, { annotation, species_ids: speciesList});
}

async function putTemporalAnnotation(recordingId: string, annotation: UpdateSpectrogramTemporalAnnotation, speciesList: number[] | null = null) {
    return axiosInstance.put<{message: string, id: number}>(`/recording/${recordingId}/temporal-annotations`, { annotation, species_ids: speciesList});
}

async function deleteAnnotation(recordingId: string, annotationId: number) {
    return axiosInstance.delete<DeletionResponse>(`/recording/${recordingId}/annotations/${annotationId}`);
}

async function deleteTemporalAnnotation(recordingId: string, annotationId: number) {
    return axiosInstance.delete<DeletionResponse>(`/recording/${recordingId}/temporal-annotations/${annotationId}`);
}

async function getOtherUserAnnotations(recordingId: string) {
    return axiosInstance.get<OtherUserAnnotations>(`/recording/${recordingId}/annotations/other_users`);
}

async function getCellLocation(cellId: number, quadrant?: 'SW' | 'NE' | 'NW' | 'SE') {
    return axiosInstance.get<GRTSCellCenter>(`/grts/${cellId}`, { params: { quadrant }});
}

interface CellIDReponse {
    grid_cell_id?: number;
    error?: string,
}
async function getCellfromLocation(latitude: number, longitude: number) {
    return axiosInstance.get<CellIDReponse>(`/grts/grid_cell_id`, {params: {latitude, longitude}});
}

export {
 uploadRecordingFile,
 getRecordings,
 getRecording,
 patchRecording,
 deleteRecording,
 getSpectrogram,
 getSpectrogramCompressed,
 getTemporalAnnotations,
 getOtherUserAnnotations,
 getSpecies,
 getAnnotations,
 patchAnnotation,
 patchTemporalAnnotation,
 putAnnotation,
 putTemporalAnnotation,
 deleteAnnotation,
 deleteTemporalAnnotation,
 getCellLocation,
 getCellfromLocation,
};