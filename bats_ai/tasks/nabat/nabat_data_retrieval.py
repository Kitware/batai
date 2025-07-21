import json
import logging
import os

from django.contrib.gis.geos import Point
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q
import requests

from bats_ai.celery import app
from bats_ai.core.models import ProcessingTask, ProcessingTaskType, Species
from bats_ai.core.models.nabat import NABatRecording, NABatRecordingAnnotation

from .tasks import generate_spectrograms

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


def get_or_create_processing_task(recording_id, request_id):
    """
    Fetch or create a ProcessingTask with the given metadata and status filters.

    Uses `get` with try-except block to handle object retrieval.

    Args:
        recording_id (int): The recording ID for the task metadata.
        request_id (str): The Celery request ID to store in the task.

    Returns:
        tuple: A tuple with the ProcessingTask instance and a boolean indicating if it was created.
    """
    # Define the metadata filter with specific keys in the JSON metadata field
    metadata_filter = {
        'type': ProcessingTaskType.NABAT_RECORDING_PROCESSING.value,
        'recordingId': recording_id,
    }

    # Try to get an existing task or handle the case where it's not found
    try:
        # Attempt to get a task based on the metadata filter and status
        processing_task = ProcessingTask.objects.get(
            Q(metadata__contains=metadata_filter)
            & Q(status__in=[ProcessingTask.Status.QUEUED, ProcessingTask.Status.RUNNING])
            & Q(celery_id=request_id)
        )
        # If task is found, return the task with False (not created)
        return processing_task, False

    except ObjectDoesNotExist:
        # If task does not exist, create a new one with the given defaults
        with transaction.atomic():
            processing_task = ProcessingTask.objects.create(
                metadata=metadata_filter,
                status=ProcessingTask.Status.QUEUED,  # Default status if creating a new task
                celery_id=request_id,
            )
        # Return the newly created task and True (created)
        return processing_task, True

    except MultipleObjectsReturned:
        # If multiple tasks are found, raise an exception (shouldn't happen if data is correct)
        raise


@app.task(bind=True)
def nabat_recording_initialize(self, recording_id: int, survey_event_id: int, api_token: str):
    processing_task, _created = get_or_create_processing_task(recording_id, self.request.id)

    processing_task.status = ProcessingTask.Status.RUNNING
    processing_task.save()
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
        response = requests.post(
            BASE_URL,
            json={'query': batch_query},
            headers=headers,
        )
    except Exception as e:
        processing_task.status = ProcessingTask.Status.ERROR
        processing_task.error = f'Error with API Request: {e}'
        processing_task.save()
        raise
    batch_data = {}

    if response.status_code == 200:
        try:
            batch_data = response.json()
        except (KeyError, TypeError, json.JSONDecodeError) as e:
            error_msg = f'Error decoding JSON response: {e}'
            logger.error(error_msg)
            processing_task.status = ProcessingTask.Status.ERROR
            processing_task.error = error_msg
            processing_task.save()
            raise
    else:
        error_msg = f'Failed to fetch data: {response.status_code}, {response.text}'
        logger.error(error_msg)
        processing_task.status = ProcessingTask.Status.ERROR
        processing_task.error = error_msg
        processing_task.save()
        raise

    self.update_state(
        state='Progress',
        meta={'description': 'Fetching Recording File'},
    )

    logger.info('Presigned URL obtained. Downloading file...')

    presigned_url = batch_data['data']['presignedUrlFromAcousticFile']['s3PresignedUrl']

    logger.info('Creating NA Bat Recording...')
    nabat_recording = create_nabat_recording_from_response(
        batch_data, recording_id, survey_event_id
    )
    generate_spectrograms(self, nabat_recording, presigned_url, processing_task)


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
        logger.error(f'Missing key: {e}')
        raise
    except Exception as e:
        logger.error(f'Error creating NABatRecording: {e}')
        raise
