import json
import logging
import tempfile

from django.contrib.gis.geos import Point
import requests

from bats_ai.celery import app
from bats_ai.core.models import ProcessingTask, Species
from bats_ai.core.models.nabat import NABatRecording, NABatRecordingAnnotation

from .tasks import generate_compress_spectrogram, generate_spectrogram, predict

# Set up logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('NABatDataRetrieval')

BASE_URL = 'https://api.sciencebase.gov/nabat-graphql/graphql'
PROJECT_ID = 7168
QUERY = """
query batsAIAcousticInfoByFileBatchId {{
  acousticFileBatchById(id: "{recording_id}") {{
    batchId
    acousticBatchByBatchId {{
      softwareBySoftwareId {{
        developer
        name
        versionNumber
      }}
      classifierByClassifierId {{
        createdDate
        description
        name
        public
        speciesClassifiersByClassifierId {{
          nodes {{
            speciesBySpeciesId {{
              speciesCode
            }}
          }}
        }}
      }}
      surveyEventBySurveyEventId {{
        createdBy
        createdDate
        eventGeometryByEventGeometryId {{
          description
          geom {{
            geojson
          }}
        }}
      }}
      createdDate
      id
    }}
    acousticFileByFileId {{
      fileName
      recordingTime
      s3Verified
      sizeBytes
    }}
    manualId
    recordingNight
    speciesByAutoId {{
      id
      speciesCode
    }}
    speciesByManualId {{
      id
      speciesCode
    }}
    autoId
  }}
}}"""

PRESIGNED_URL_QUERY = """
query batsAIAcousticPresignedUrlByBucketKey {{
  s3FileServiceDownloadFile(
    bucket: "nabat-prod-acoustic-recordings",
    key: "{key}"
  ) {{
    s3PresignedUrl
    success
    message
  }}
}}
"""


@app.task(bind=True)
def nabat_recording_initialize(self, recording_id: int, api_token: str):
    processing_task = ProcessingTask.objects.filter(celery_id=self.request.id)
    processing_task.update(status=ProcessingTask.Status.RUNNING)
    headers = {'Authorization': f'Bearer {api_token}', 'Content-Type': 'application/json'}
    base_query = QUERY.format(recording_id=recording_id)
    self.update_state(
        state='Progress',
        meta={'description': 'Fetching NAbat Recording Data'},
    )
    try:
        response = requests.post(BASE_URL, json={'query': base_query}, headers=headers)
    except Exception as e:
        processing_task.update(
            status=ProcessingTask.Status.ERROR, error=f'Error with API Reqeust: {e}'
        )
        raise
    batch_data = {}

    if response.status_code == 200:
        try:
            batch_data = response.json()
        except (KeyError, TypeError, json.JSONDecodeError) as e:
            logger.error(f'Error processing batch data: {e}')
            processing_task.update(
                status=ProcessingTask.Status.ERROR, error=f'Error processing batch data: {e}'
            )
            raise
    else:
        logger.error(f'Failed to fetch data: {response.status_code}, {response.text}')
        processing_task.update(
            status=ProcessingTask.Status.ERROR,
            error=f'Failed to fetch data: {response.status_code}, {response.text}',
        )
        return

    try:
        file_name = batch_data['data']['acousticFileBatchById']['acousticFileByFileId']['fileName']
        file_key = f'{PROJECT_ID}/{file_name}'
    except (KeyError, TypeError) as e:
        logger.error(f'Error extracting file information: {e}')
        processing_task.update(
            status=ProcessingTask.Status.ERROR, error=f'Error extracting file information: {e}'
        )
        raise
    presigned_query = PRESIGNED_URL_QUERY.format(key=file_key)
    logger.info('Fetching presigned URL...')
    self.update_state(
        state='Progress',
        meta={'description': 'Fetching Recording File'},
    )

    response = requests.post(BASE_URL, json={'query': presigned_query}, headers=headers)

    if response.status_code != 200:
        logger.error(f'Failed to fetch presigned URL: {response.status_code}, {response.text}')
        processing_task.update(
            status=ProcessingTask.Status.ERROR,
            error=f'Failed to fetch presigned URL: {response.status_code}, {response.text}',
        )
        raise

    try:
        presigned_data = response.json()
        url_info = presigned_data['data']['s3FileServiceDownloadFile']
        presigned_url = url_info['s3PresignedUrl']
        if not url_info['success']:
            logger.error(f'Failed to get presigned URL: {url_info["message"]}')
            processing_task.update(
                status=ProcessingTask.Status.ERROR,
                error=f'Failed to get presigned URL: {url_info["message"]}',
            )
            return
    except (KeyError, TypeError) as e:
        logger.error(f'Error extracting presigned URL: {e}')
        processing_task.update(
            status=ProcessingTask.Status.ERROR, error=f'Error extracting presigned URL: {e}'
        )
        raise

    logger.info('Presigned URL obtained. Downloading file...')

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            file_response = requests.get(presigned_url, stream=True)
            if file_response.status_code == 200:
                for chunk in file_response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
                temp_file_path = temp_file.name  # This gives the path of the temp file
                logger.info(f'File downloaded to temporary file: {temp_file_path}')

                # Now create the NABatRecording using the response data
                logger.info('Creating NA Bat Recording...')
                nabat_recording = create_nabat_recording_from_response(batch_data, recording_id)

                # Call generate_spectrogram with the nabat_recording and the temporary file
                logger.info('Generating spectrogram...')
                self.update_state(
                    state='Progress',
                    meta={'description': 'Generating Spectrogram'},
                )

                spectrogram = generate_spectrogram(nabat_recording, open(temp_file_path, 'rb'))
                logger.info('Generating compressed spectrogram...')
                self.update_state(
                    state='Progress',
                    meta={'description': 'Generating Compressed Spectrogram'},
                )

                compressed_spectrogram = generate_compress_spectrogram(
                    nabat_recording.pk, spectrogram.pk
                )
                logger.info('Running Prediction...')
                self.update_state(
                    state='Progress',
                    meta={'description': 'Running Prediction'},
                )

                try:
                    predict(compressed_spectrogram.pk)
                except Exception as e:
                    logger.error(f'Error Performing Prediction: {e}')
                    processing_task.update(
                        status=ProcessingTask.Status.ERROR,
                        error=f'Error extracting presigned URL: {e}',
                    )
                    raise
                processing_task.update(status=ProcessingTask.Status.COMPLETE)

            else:
                processing_task.update(
                    status=ProcessingTask.Status.ERROR,
                    error=f'Failed to download file: {file_response.status_code}',
                )
                logger.error(f'Failed to download file: {file_response.status_code}')
    except Exception as e:
        processing_task.update(status=ProcessingTask.Status.ERROR, error=str(e))
        logger.error(f'Error handling file download or temporary file: {e}')
        raise


def create_nabat_recording_from_response(response_data, recording_id):
    try:
        # Extract the batch data from the response
        nabat_recording_data = response_data['data']['acousticFileBatchById']

        # Extract nested data from the response
        software_name = nabat_recording_data['acousticBatchByBatchId']['softwareBySoftwareId'][
            'name'
        ]
        software_developer = nabat_recording_data['acousticBatchByBatchId']['softwareBySoftwareId'][
            'developer'
        ]
        software_version = nabat_recording_data['acousticBatchByBatchId']['softwareBySoftwareId'][
            'versionNumber'
        ]

        # Optional fields
        recording_location_data = nabat_recording_data['acousticBatchByBatchId'][
            'surveyEventBySurveyEventId'
        ]['eventGeometryByEventGeometryId']['geom']['geojson']

        # Create geometry for the recording location if available
        if recording_location_data:
            coordinates = recording_location_data.get('coordinates', [])
            recording_location = (
                Point(coordinates[0], coordinates[1]) if len(coordinates) == 2 else None
            )
        else:
            recording_location = None

        # Get the species info
        species_code_auto = nabat_recording_data.get('speciesByAutoId', {}).get(
            'speciesCode', False
        )
        species_code_manual = nabat_recording_data.get('speciesByManualId', {}).get(
            'speciesCode', False
        )

        # Create the NABatRecording instance
        nabat_recording = NABatRecording.objects.create(
            recording_id=recording_id,
            name=f'Recording {recording_id}',
            software_name=software_name,
            software_developer=software_developer,
            software_version=software_version,
            recording_location=recording_location,
        )

        if species_code_auto:
            species = Species.objects.filter(species_code=species_code_auto)
            if species:
                nabat_recording_annotation = NABatRecordingAnnotation.objects.create(
                    nabat_recording=nabat_recording,
                    comments='NABat Auto Annotation',
                    model='NABat Auto Annotation',
                    confidence=1.0,
                )
                nabat_recording_annotation.species.set(species)
                nabat_recording_annotation.save()

        if species_code_manual:
            species = Species.objects.filter(species_code=species_code_manual)
            if species:
                nabat_recording_annotation = NABatRecordingAnnotation.objects.create(
                    nabat_recording=nabat_recording,
                    comments='NABat Manual',
                    model='NABat Manual Annotation',
                    confidence=1.0,
                )
                nabat_recording_annotation.species.set(species)
                nabat_recording_annotation.save()

        return nabat_recording

    except KeyError as e:
        print(f'Missing key: {e}')
        return None
    except Exception as e:
        print(f'Error creating NABatRecording: {e}')
        return None
