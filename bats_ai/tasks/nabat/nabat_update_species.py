import logging

import requests

from bats_ai.celery import app
from bats_ai.core.models import ProcessingTask, Species

# Set up logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('NABatGetSpecies')

BASE_URL = 'https://api.sciencebase.gov/nabat-graphql/graphql'
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


@app.task(bind=True)
def update_nabat_species(self, api_token: str):
    processing_task = ProcessingTask.objects.filter(celery_id=self.request.id)
    processing_task.update(status=ProcessingTask.Status.RUNNING)

    headers = {'Authorization': f'Bearer {api_token}', 'Content-Type': 'application/json'}
    try:
        response = requests.post(BASE_URL, json={'query': QUERY}, headers=headers)
        response.raise_for_status()
    except Exception as e:
        processing_task.update(
            status=ProcessingTask.Status.ERROR, error=f'Error with API request: {e}'
        )
        raise

    try:
        data = response.json()
        species_list = data.get('data', {}).get('allSpecies', {}).get('nodes', [])

        for species_data in species_list:
            species_id = species_data.get('id')
            if species_id is None:
                logger.warning(f'Species without an ID encountered: {species_data}')
                continue

            Species.objects.update_or_create(
                id=species_id,  # force the pk to match the external ID
                defaults={
                    'species_code': species_data.get('speciesCode'),
                    'species_code_6': species_data.get('speciesCode6'),
                    'genus': species_data.get('genus'),
                    'family': species_data.get('family'),
                    'species': species_data.get('species'),
                    'common_name': species_data.get('commonName'),
                },
            )

        processing_task.update(status=ProcessingTask.Status.COMPLETE)
        logger.info(f'Successfully updated {len(species_list)} species.')
    except Exception as e:
        processing_task.update(
            status=ProcessingTask.Status.ERROR, error=f'Error processing species data: {e}'
        )
        raise
