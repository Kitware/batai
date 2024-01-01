import { Axios } from 'axios';
import S3FileFieldClient from 'django-s3-file-field';

let s3ffClient: S3FileFieldClient;

export function createS3ffClient(axiosInstance: Axios) {
  s3ffClient = new S3FileFieldClient({
    baseUrl: `${import.meta.env.VUE_APP_API_ROOT}/s3-upload`,
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    apiConfig: axiosInstance.defaults, // This argument is optional
  });
  return s3ffClient;
}

export function getS3ffClient() {
  if (s3ffClient === undefined) {
    throw new Error('s3ffClient has not been initialized');
  } else {
    return s3ffClient;
  }
}