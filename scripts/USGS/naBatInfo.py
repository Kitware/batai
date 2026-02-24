from __future__ import annotations

import base64
import json
import logging

import click
import requests

# Set up logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variable for authorization token
AUTH_TOKEN = ""
BASE_URL = "https://api.sciencebase.gov/nabat-graphql/graphql"
SURVEY_ID = 591184
SURVEY_EVENT_ID = 4768736
ACOUSTIC_FILE_ID = 190255936
PROJECT_ID = 7168
BATCH_ID = 319479412
SOFTWARE_ID = 81
# GraphQL queries
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


def decode_jwt(token):
    # Split the token into parts
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT token format")

    # JWT uses base64url encoding, so need to fix padding
    payload = parts[1]
    padding = "=" * (4 - (len(payload) % 4))  # Fix padding if needed
    payload += padding

    # Decode the payload
    decoded_bytes = base64.urlsafe_b64decode(payload)
    decoded_str = decoded_bytes.decode("utf-8")

    # Parse JSON
    return json.loads(decoded_str)


@click.command()
def fetch_and_save():
    """Fetch data using GraphQL and save to output.json."""
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}", "Content-Type": "application/json"}

    # Fetch batch data
    logger.info("Fetching batch data...")
    batch_query = QUERY % {
        "acoustic_file_id": ACOUSTIC_FILE_ID,
        "survey_event_id": SURVEY_EVENT_ID,
        "software_id": SOFTWARE_ID,
    }
    response = requests.post(BASE_URL, json={"query": batch_query}, headers=headers)
    batch_data = {}

    print(response.text)

    if response.status_code == 200:
        try:
            batch_data = response.json()
            batch_data["jwt"] = decode_jwt(AUTH_TOKEN)
            with open("output.json", "w") as f:
                json.dump(batch_data, f, indent=2)
            logger.info("Data successfully fetched and saved to output.json")
        except (KeyError, TypeError, json.JSONDecodeError) as e:
            logger.exception(f"Error processing batch data: {e}")
            return
    else:
        logger.error(f"Failed to fetch data: {response.status_code}, {response.text}")
        return

    # Extract file name and key
    file_name = batch_data["data"]["acousticFileById"]["fileName"]

    # Fetch presigned URL
    presigned_url = batch_data["data"]["presignedUrlFromAcousticFile"]["s3PresignedUrl"]
    # Download the file
    file_response = requests.get(presigned_url, stream=True)
    if file_response.status_code == 200:
        try:
            with open(file_name, "wb") as f:
                f.writelines(file_response.iter_content(chunk_size=8192))
            logger.info(f"File downloaded: {file_name}")
        except Exception as e:
            logger.exception(f"Error saving the file: {e}")
    else:
        logger.error(f"Failed to download file: {file_response.status_code}")


if __name__ == "__main__":
    fetch_and_save()
