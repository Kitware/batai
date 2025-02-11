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
PROJECT_ID = 7168
BATCH_ID = 319479412
# GraphQL queries
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
}}
"""

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


@click.command()
def fetch_and_save():
    """Fetch data using GraphQL and save to output.json"""
    headers = {'Authorization': f'Bearer {AUTH_TOKEN}', 'Content-Type': 'application/json'}

    # Fetch batch data
    logger.info('Fetching batch data...')
    batch_query = QUERY.format(batch_id=BATCH_ID)
    response = requests.post(BASE_URL, json={'query': batch_query}, headers=headers)
    batch_data = {}

    if response.status_code == 200:
        try:
            batch_data = response.json()
            with open('output.json', 'w') as f:
                json.dump(batch_data, f, indent=2)
            logger.info('Data successfully fetched and saved to output.json')
        except (KeyError, TypeError, json.JSONDecodeError) as e:
            logger.error(f'Error processing batch data: {e}')
            return
    else:
        logger.error(f'Failed to fetch data: {response.status_code}, {response.text}')
        return

    # Extract file name and key
    try:
        file_name = batch_data['data']['acousticFileBatchById']['acousticFileByFileId']['fileName']
        file_key = f'{PROJECT_ID}/{file_name}'
    except (KeyError, TypeError) as e:
        logger.error(f'Error extracting file information: {e}')
        return

    # Fetch presigned URL
    presigned_query = PRESIGNED_URL_QUERY.format(key=file_key)
    logger.info('Fetching presigned URL...')
    response = requests.post(BASE_URL, json={'query': presigned_query}, headers=headers)

    if response.status_code != 200:
        logger.error(f'Failed to fetch presigned URL: {response.status_code}, {response.text}')
        return

    try:
        presigned_data = response.json()
        url_info = presigned_data['data']['s3FileServiceDownloadFile']
        presigned_url = url_info['s3PresignedUrl']
        if not url_info['success']:
            logger.error(f'Failed to get presigned URL: {url_info["message"]}')
            return
    except (KeyError, TypeError) as e:
        logger.error(f'Error extracting presigned URL: {e}')
        return

    logger.info('Presigned URL obtained. Downloading file...')

    # Download the file
    file_response = requests.get(presigned_url, stream=True)
    if file_response.status_code == 200:
        try:
            with open(file_name, 'wb') as f:
                for chunk in file_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f'File downloaded: {file_name}')
        except Exception as e:
            logger.error(f'Error saving the file: {e}')
    else:
        logger.error(f'Failed to download file: {file_response.status_code}')


if __name__ == '__main__':
    fetch_and_save()
