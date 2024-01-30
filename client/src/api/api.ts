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
    equipment?: string,
    comments?: string;
    recording_location?: null | [number, number],
    grts_cell_id?: null | number;
    grts_cell?: null | number;
    public: boolean;
    userMadeAnnotations: boolean;
    userAnnotations: number;
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
}

export interface UpdateSpectrogramAnnotation {
    start_time?: number;
    end_time?: number;
    low_freq?: number;
    high_freq?: number;
    id?: number;
    editing?: boolean;
    species?: Species[];
    comments?: string;
}

export interface Spectrogram {
    'base64_spectrogram': string;
    url?: string;
    filename?: string;
    annotations?: SpectrogramAnnotation[];
    spectroInfo?: SpectroInfo;

}

interface PaginatedNinjaResponse<T> {
    count: number,
    items: T[],
}



export const axiosInstance = axios.create({
  baseURL: import.meta.env.VUE_APP_API_ROOT as string,
});


async function uploadRecordingFile(file: File, name: string, recorded_date: string, equipment: string, comments: string, publicVal = false ) {
    const formData = new FormData();
    formData.append('audio_file', file);
    formData.append('name', name);
    formData.append('recorded_date', recorded_date);
    formData.append('equipment', equipment);
    formData.append('comments', comments);
    
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

  async function patchRecording(recordingId: number, name: string, recorded_date: string, equipment: string, comments: string, publicVal = false ) {
    await axiosInstance.patch(`/recording/${recordingId}`, 
        { 
            name, 
            recorded_date, 
            equipment, 
            comments, 
            publicVal 
        },
        {
            headers: {
                'Content-Type': 'application/json',
            }
        }
    );
}
  
async function getRecordings(getPublic=false) {
    return axiosInstance.get<Recording[]>(`/recording?public=${getPublic}`);
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

async function getSpecies() {
    return axiosInstance.get<Species[]>('/species/');
}

async function patchAnnotation(recordingId: string, annotationId: number, annotation: UpdateSpectrogramAnnotation, speciesList: number[] = []) {
    return axiosInstance.patch(`/recording/${recordingId}/annotations/${annotationId}`, { annotation, species_ids: speciesList});
}

async function putAnnotation(recordingId: string, annotation: UpdateSpectrogramAnnotation, speciesList: number[] = []) {
    return axiosInstance.put<{message: string, id: number}>(`/recording/${recordingId}/annotations`, { annotation, species_ids: speciesList});
}

async function deleteAnnotation(recordingId: string, annotationId: number) {
    return axiosInstance.delete(`/recording/${recordingId}/annotations/${annotationId}`);
}

export {
 uploadRecordingFile,
 getRecordings,
 patchRecording,
 getSpectrogram,
 getSpectrogramCompressed,
 getSpecies,
 getAnnotations,
 patchAnnotation,
 putAnnotation,
 deleteAnnotation
};