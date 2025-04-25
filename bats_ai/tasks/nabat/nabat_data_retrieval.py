import json
import logging
import os
import tempfile

from django.contrib.gis.geos import Point
import requests

from bats_ai.celery import app
from bats_ai.core.models import Configuration, ProcessingTask, ProcessingTaskType, Species
from bats_ai.core.models.nabat import NABatRecording, NABatRecordingAnnotation

from .tasks import generate_compress_spectrogram, generate_spectrogram, predict

# Set up logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('NABatDataRetrieval')

BASE_URL = os.environ.get('NABAT_API_URL', 'https://api.sciencebase.gov/nabat-graphql/graphql')
SOFTWARE_ID = 81
QUERY = """
query fetchAcousticAndSurveyEventInfo {
  presignedUrlFromAcousticFile(acousticFileId: "%(acoustic_file_id)s") {
    s3PresignedUrl
  }
  surveyEventById(id: "%(survey_event_id)d") {
    createdBy
    createdDate
    eventGeometryByEventGeometryId {
      description
      geom {
        geojson
      }
    }
    acousticBatchesBySurveyEventId(filter: {softwareId: {equalTo:%(software_id)d}}) {
      nodes {
        id
        acousticFileBatchesByBatchId(filter: {fileId: {equalTo: "%(acoustic_file_id)s"}}) {
          nodes {
            autoId
            manualId
            vetter
            speciesByManualId {
              speciesCode
            }
          }
        }
      }
    }
  }
  acousticFileById(id: "%(acoustic_file_id)d") {
    fileName
    recordingTime
    s3Verified
    sizeBytes
  }
}
"""


@app.task(bind=True)
def nabat_recording_initialize(self, recording_id: int, survey_event_id: int, api_token: str):
    processing_task, _created = ProcessingTask.objects.get_or_create(
        metadata={
            'type': ProcessingTaskType.NABAT_RECORDING_PROCESSING.value,
            'recordingId': recording_id,
        },
        defaults={'celery_id': self.request.id},
    )
    processing_task.update(status=ProcessingTask.Status.RUNNING)
    headers = {'Authorization': f'Bearer {api_token}', 'Content-Type': 'application/json'}
    batch_query = QUERY % {
        'acoustic_file_id': recording_id,
        'survey_event_id': survey_event_id,
        'software_id': SOFTWARE_ID,
    }
    self.update_state(
        state='Progress',
        meta={'description': 'Fetching NAbat Recording Data'},
    )
    try:
        response = requests.post(BASE_URL, json={'query': batch_query}, headers=headers)
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

    self.update_state(
        state='Progress',
        meta={'description': 'Fetching Recording File'},
    )

    logger.info('Presigned URL obtained. Downloading file...')

    presigned_url = batch_data['data']['presignedUrlFromAcousticFile']['s3PresignedUrl']

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
                nabat_recording = create_nabat_recording_from_response(
                    batch_data, recording_id, survey_event_id
                )

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
                    config = Configuration.objects.first()
                    if config and config.run_inference_on_upload:
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


def create_nabat_recording_from_response(response_data, recording_id, survey_event_id):
    try:
        # Extract the batch data from the response
        nabat_recording_data = response_data['data']

        # Optional fields
        recording_location_data = nabat_recording_data['surveyEventById'][
            'eventGeometryByEventGeometryId'
        ]['geom']['geojson']
        file_name = nabat_recording_data['acousticFileById']['fileName']

        # Create geometry for the recording location if available
        if recording_location_data:
            coordinates = recording_location_data.get('coordinates', [])
            recording_location = (
                Point(coordinates[0], coordinates[1]) if len(coordinates) == 2 else None
            )
        else:
            recording_location = None

        # Create the NABatRecording instance
        nabat_recording = NABatRecording.objects.create(
            recording_id=recording_id,
            survey_event_id=survey_event_id,
            name=file_name,
            recording_location=recording_location,
        )

        acoustic_batches_nodes = nabat_recording_data['surveyEventById'][
            'acousticBatchesBySurveyEventId'
        ]['nodes']
        if len(acoustic_batches_nodes) > 0:
            batch_data = acoustic_batches_nodes[0]['acousticFileBatchesByBatchId']['nodes']
        for node in batch_data:
            species_id = node.get('manualId', False)
            if species_id is not False:
                annotation = NABatRecordingAnnotation.objects.create(
                    nabat_recording=nabat_recording,
                    user_email=node['vetter'],
                )
                species = Species.objects.get(pk=species_id)
                annotation.species.add(species)

        return nabat_recording

    except KeyError as e:
        print(f'Missing key: {e}')
        return None
    except Exception as e:
        print(f'Error creating NABatRecording: {e}')
        return None
