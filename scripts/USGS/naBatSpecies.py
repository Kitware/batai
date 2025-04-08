import base64
import json
import logging

import click
import requests

# Set up logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variable for authorization token
AUTH_TOKEN = ''
BASE_URL = 'https://api.sciencebase.gov/nabat-graphql/graphql'
# GraphQL queries
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


def decode_jwt(token):
    # Split the token into parts
    parts = token.split('.')
    if len(parts) != 3:
        raise ValueError('Invalid JWT token format')

    # JWT uses base64url encoding, so need to fix padding
    payload = parts[1]
    padding = '=' * (4 - (len(payload) % 4))  # Fix padding if needed
    payload += padding

    # Decode the payload
    decoded_bytes = base64.urlsafe_b64decode(payload)
    decoded_str = decoded_bytes.decode('utf-8')

    # Parse JSON
    return json.loads(decoded_str)


@click.command()
def fetch_and_save():
    """Fetch data using GraphQL and save to speceis.json"""
    headers = {'Authorization': f'Bearer {AUTH_TOKEN}', 'Content-Type': 'application/json'}

    # Fetch batch data
    logger.info('Fetching batch data...')
    response = requests.post(BASE_URL, json={'query': QUERY}, headers=headers)
    batch_data = {}

    print(response.text)

    if response.status_code == 200:
        try:
            batch_data = response.json()
            batch_data['jwt'] = decode_jwt(AUTH_TOKEN)
            with open('species.json', 'w') as f:
                json.dump(batch_data, f, indent=2)
            logger.info('Data successfully fetched and saved to output.json')
        except (KeyError, TypeError, json.JSONDecodeError) as e:
            logger.error(f'Error processing batch data: {e}')
            return
    else:
        logger.error(f'Failed to fetch data: {response.status_code}, {response.text}')
        return


if __name__ == '__main__':
    fetch_and_save()
