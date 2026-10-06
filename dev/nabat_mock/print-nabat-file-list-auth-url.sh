#!/usr/bin/env bash
# Prints a Keycloak authorization URL you can paste into a browser to kick off the
# NABat -> batai file-list redirect flow, the same way print-nabat-auth-url.sh does
# for a single recording. With docker-compose-nabat-mock.yml's nabat-mock service also
# up, this drives create_nabat_file_list end to end: Keycloak login, code exchange,
# then POST /nabat/file-list/create against the mocked NABat GraphQL API.
set -euo pipefail

KEYCLOAK_URL=${KEYCLOAK_URL:-http://localhost:8081/auth}
REALM=${REALM:-NABAT}
CLIENT_ID=${CLIENT_ID:-batai}
BATAI_WEB_URL=${BATAI_WEB_URL:-http://localhost:8080/}
# nabat-mock returns the same single-file list for any id - see mock_server.py.
FILE_LIST_ID=${FILE_LIST_ID:-1}
# Left empty by default to mirror production, which omits `scope` and relies on the
# client's default scopes. Set to "openid nabat-service-audience" to request the optional
# audience scope instead.
SCOPE=${SCOPE:-}

redirect_uri="${BATAI_WEB_URL%/}/nabat/file-list/auth/?fileListId=${FILE_LIST_ID}"

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
