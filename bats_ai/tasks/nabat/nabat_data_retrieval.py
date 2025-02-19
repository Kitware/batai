import json
import logging
import tempfile

from django.contrib.gis.geos import Point
import requests

from bats_ai.celery import app
from bats_ai.core.models import ProcessingTask, Species
from bats_ai.core.models.nabat import AcousticBatch

from .tasks import generate_compress_spectrogram, generate_spectrogram, predict

# Set up logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('NABatDataRetrieval')

BASE_URL = 'https://api.sciencebase.gov/nabat-graphql/graphql'
PROJECT_ID = 7168
QUERY = """
query batsAIAcousticInfoByFileBatchId {{
  acousticFileBatchById(id: "{batch_id}") {{
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
def acoustic_batch_initialize(self, batch_id: int, api_token: str):
    processing_task = ProcessingTask.objects.filter(celery_id=self.request.id)
    processing_task.update(status=ProcessingTask.Status.RUNNING)
    headers = {'Authorization': f'Bearer {api_token}', 'Content-Type': 'application/json'}
    base_query = QUERY.format(batch_id=batch_id)
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

                # Now create the AcousticBatch using the response data
                logger.info('Creating Acoustic Batch...')
                acoustic_batch = create_acoustic_batch_from_response(batch_data, batch_id)

                # Call generate_spectrogram with the acoustic_batch and the temporary file
                logger.info('Generating spectrogram...')
                self.update_state(
                    state='Progress',
                    meta={'description': 'Generating Spectrogram'},
                )

                spectrogram = generate_spectrogram(acoustic_batch, open(temp_file_path, 'rb'))
                logger.info('Generating compressed spectrogram...')
                self.update_state(
                    state='Progress',
                    meta={'description': 'Generating Compressed Spectrogram'},
                )

                compressed_spectrogram = generate_compress_spectrogram(
                    acoustic_batch.pk, spectrogram.pk
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


def create_acoustic_batch_from_response(response_data, batch_id):
    try:
        # Extract the batch data from the response
        acoustic_batch_data = response_data['data']['acousticFileBatchById']

        # Extract nested data from the response
        software_name = acoustic_batch_data['acousticBatchByBatchId']['softwareBySoftwareId'][
            'name'
        ]
        software_developer = acoustic_batch_data['acousticBatchByBatchId']['softwareBySoftwareId'][
            'developer'
        ]
        software_version = acoustic_batch_data['acousticBatchByBatchId']['softwareBySoftwareId'][
            'versionNumber'
        ]

        # Optional fields
        recording_location_data = acoustic_batch_data['acousticBatchByBatchId'][
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
        species_code = acoustic_batch_data['speciesByAutoId']['speciesCode']
        species = Species.objects.filter(species_code=species_code).first()

        # Create the AcousticBatch instance
        acoustic_batch = AcousticBatch.objects.create(
            batch_id=batch_id,
            name=f'Batch {batch_id}',
            software_name=software_name,
            software_developer=software_developer,
            software_version=software_version,
            recording_location=recording_location,
            nabat_auto_species=species,
        )

        return acoustic_batch

    except KeyError as e:
        print(f'Missing key: {e}')
        return None
    except Exception as e:
        print(f'Error creating AcousticBatch: {e}')
        return None
