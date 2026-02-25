from __future__ import annotations

import logging

from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
import requests

from bats_ai.celery import app
from bats_ai.core.models import ProcessingTask, ProcessingTaskType, Species

# Set up logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NABatGetSpecies")

QUERY = """
query GetAllSpeciesOptions {
  allSpecies {
    nodes {
      id
      species
      speciesCode
      speciesCode6
      genus
      family
      commonName
    }
  }
}
"""


def get_or_create_processing_task(request_id):
    """
    Fetch or creat a ProcessingTask with the given metadata and status filters.

    Args:
        request_id (str): The Celery request ID to store in the task.

    Returns:
        tuple: A tuple with the ProcessingTask instance and a boolean indicating if it was created.
    """
    metadata_filter = {
        "type": ProcessingTaskType.UPDATING_SPECIES.value,
    }

    # Try to get an existing task or handle the case where it's not found
    try:
        # Attempt to get a task based on the metadata filter and status
        processing_task = ProcessingTask.objects.get(
            metadata__contains=metadata_filter,
            status__in=[ProcessingTask.Status.QUEUED, ProcessingTask.Status.RUNNING],
        )
        # If task is found, return the task with False (not created)
        return processing_task, False

    except ObjectDoesNotExist:
        # If task does not exist, create a new one with the given defaults
        processing_task = ProcessingTask.objects.create(
            metadata={"type": ProcessingTaskType.UPDATING_SPECIES.value},
            status=ProcessingTask.Status.QUEUED,  # Default status if creating a new task
            celery_id=request_id,
        )
        # Return the newly created task and True (created)
        return processing_task, True

    except MultipleObjectsReturned:
        # If multiple tasks are found, raise an exception (shouldn't happen if data is correct)
        raise


@app.task(bind=True)
def update_nabat_species(self):
    processing_task, _created = get_or_create_processing_task(self.request.id)
    processing_task.status = ProcessingTask.Status.RUNNING
    processing_task.save()

    try:
        response = requests.post(settings.BATAI_NABAT_API_URL, json={"query": QUERY}, timeout=30)
        response.raise_for_status()
    except Exception as e:
        processing_task.status = ProcessingTask.Status.ERROR
        processing_task.error = f"Error with API request: {e}"
        processing_task.save()
        raise

    try:
        data = response.json()
        species_list = data.get("data", {}).get("allSpecies", {}).get("nodes", [])

        for species_data in species_list:
            species_id = species_data.get("id")
            if species_id is None:
                logger.warning(f"Species without an ID encountered: {species_data}")
                continue

            Species.objects.update_or_create(
                id=species_id,  # force the pk to match the external ID
                defaults={
                    "species_code": species_data.get("speciesCode"),
                    "species_code_6": species_data.get("speciesCode6"),
                    "genus": species_data.get("genus"),
                    "family": species_data.get("family"),
                    "species": species_data.get("species"),
                    "common_name": species_data.get("commonName"),
                },
            )

        processing_task.status = ProcessingTask.Status.COMPLETE
        processing_task.save()
        logger.info(f"Successfully updated {len(species_list)} species.")
    except Exception as e:
        processing_task.status = ProcessingTask.Status.ERROR
        processing_task.error = f"Error processing species data: {e}"
        processing_task.save()
        raise
