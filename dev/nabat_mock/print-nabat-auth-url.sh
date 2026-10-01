#!/usr/bin/env bash
# Prints a Keycloak authorization URL you can paste into a browser to kick off the
# NABat -> batai redirect flow for real, the same way clicking "open in batai" in the
# NABat portal does (see scripts/USGS/sampleUrl.txt for the legacy apiToken-URL equivalent).
# With docker-compose-nabat-mock.yml's nabat-mock service also up, this drives the full
# pipeline end to end: Keycloak login, code exchange, and then a real fetch + spectrogram
# generation against the mocked NABat GraphQL API and the existing minio service.
set -euo pipefail

KEYCLOAK_URL=${KEYCLOAK_URL:-http://localhost:8081/auth}
REALM=${REALM:-NABAT}
CLIENT_ID=${CLIENT_ID:-batai}
BATAI_WEB_URL=${BATAI_WEB_URL:-http://localhost:8080/}
RECORDING_ID=${RECORDING_ID:-190255936}
SURVEY_EVENT_ID=${SURVEY_EVENT_ID:-4768736}
# Left empty by default to mirror production, which omits `scope` and relies on the
# client's default scopes. Set to "openid nabat-service-audience" to request the optional
# audience scope instead.
SCOPE=${SCOPE:-}

redirect_uri="${BATAI_WEB_URL%/}/nabat/auth/?recordingId=${RECORDING_ID}&surveyEventId=${SURVEY_EVENT_ID}"

python3 -c "
import urllib.parse

params = {
    'client_id': '$CLIENT_ID',
    'response_type': 'code',
    'redirect_uri': '$redirect_uri',
}
scope = '$SCOPE'.strip()
if scope:
    params['scope'] = scope

print('${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/auth?' + urllib.parse.urlencode(params))
"
