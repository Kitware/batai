#!/usr/bin/env bash
# Reproduces the NABat "open in batai" redirect flow against the local Keycloak
# (docker-compose-keycloak.yml) without a browser: authenticates as a test user,
# follows the same authorization-code redirect NABat's portal triggers, then
# exchanges the resulting code for a token exactly like batai's backend would.
set -euo pipefail

KEYCLOAK_URL=${KEYCLOAK_URL:-http://localhost:8081/auth}
REALM=${REALM:-NABAT}
CLIENT_ID=${CLIENT_ID:-batai}
CLIENT_SECRET=${CLIENT_SECRET:-batai-local-dev-secret}
REDIRECT_URI=${REDIRECT_URI:-http://localhost:8080/callback}
NABAT_USERNAME=${NABAT_USERNAME:-testuser}
NABAT_PASSWORD=${NABAT_PASSWORD:-testuser}
# Optional client scopes (e.g. nabat-service-audience) are only granted if requested here.
SCOPE=${SCOPE:-openid}

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT
jar="$workdir/cookies.txt"

echo "== Step 1: GET the authorization endpoint (client_id=$CLIENT_ID, scope=$SCOPE) =="
curl -s -c "$jar" -b "$jar" -G "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/auth" \
  --data-urlencode "client_id=$CLIENT_ID" \
  --data-urlencode "response_type=code" \
  --data-urlencode "scope=$SCOPE" \
  --data-urlencode "redirect_uri=$REDIRECT_URI" \
  -o "$workdir/auth_page.html"

action_url=$(grep -o 'action="[^"]*"' "$workdir/auth_page.html" | head -1 | sed -e 's/action="//' -e 's/"$//' -e 's/&amp;/\&/g')
if [[ -z "$action_url" ]]; then
  echo "Could not find login form action in the authorization response - is Keycloak up and the realm imported?" >&2
  exit 1
fi

echo "== Step 2: submit the login form as $NABAT_USERNAME =="
curl -s -i -c "$jar" -b "$jar" "$action_url" \
  --data-urlencode "username=$NABAT_USERNAME" \
  --data-urlencode "password=$NABAT_PASSWORD" \
  -o /dev/null -D "$workdir/login_headers.txt"

location=$(grep -i "^location:" "$workdir/login_headers.txt" | sed 's/^[Ll]ocation: //' | tr -d '\r')
if [[ -z "$location" ]]; then
  echo "Login did not redirect - check NABAT_USERNAME/NABAT_PASSWORD, or inspect $workdir/login_headers.txt" >&2
  exit 1
fi
echo "Redirected to: $location"

code=$(grep -oP '(?<=[?&]code=)[^&]+' <<< "$location")
if [[ -z "$code" ]]; then
  echo "No code param in the redirect - the login likely failed" >&2
  exit 1
fi

echo "== Step 3: exchange the code for a token, as $CLIENT_ID's backend would =="
token_args=(-d grant_type=authorization_code -d "client_id=$CLIENT_ID")
[[ -n "$CLIENT_SECRET" ]] && token_args+=(-d "client_secret=$CLIENT_SECRET")
token_response=$(curl -s -X POST "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token" \
  "${token_args[@]}" \
  --data-urlencode "redirect_uri=$REDIRECT_URI" \
  --data-urlencode "code=$code")

python3 -c "
import json, sys, base64
d = json.loads('''$token_response''')
if 'access_token' not in d:
    print('Token endpoint error:', d)
    sys.exit(1)
payload = d['access_token'].split('.')[1]
payload += '=' * (-len(payload) % 4)
claims = json.loads(base64.urlsafe_b64decode(payload))
print(json.dumps(claims, indent=2))
"
