import base64
import json
import logging
import os
from uuid import uuid4

from django.db import transaction
from django.http import HttpRequest, JsonResponse
from ninja import Schema
from ninja.router import Router
import requests

from bats_ai.core.models.nabat import NABatSession

logger = logging.getLogger(__name__)
router = Router()


class RefreshSchema(Schema):
    refresh_token: str
    access_token: str


SOFTWARE_ID = int(os.environ.get('NABAT_SOFTWARE_ID', 81))
BASE_URL = os.environ.get('NABAT_API_URL', 'https://api.sciencebase.gov/nabat-graphql/graphql')
QUERY = """
mutation refreshTokens {
    authTokenRefresh(input: { refreshToken: "%(refresh_token)s" }) {
        access_token
        refresh_token
        user_id
    }
}
"""


def get_new_tokens(auth_token: str, refresh_token: str):
    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json'
    }
    query = QUERY % {'refresh_token': refresh_token}
    json_response = {}
    try:
        response = requests.post(BASE_URL, json={'query': query}, headers=headers)
        json_response = response.json()
        if json_response.get('errors'):
            logger.error(f'API Error: {json_response["errors"]}')
            return {'error': json_response['errors'], 'status': 500}
    except Exception as e:
        logger.error(f'API request error: {e}')
        return {'error': 'Failed to connect to NABat API', 'status': 500}
    # TODO take the response and return the updated tokens
    new_tokens = json_response.get('data', {}).get('authTokenRefresh', None)
    if not new_tokens:
        logger.error('Failed to determine tokens from API response')
        return {'error': 'Failed to parse NABat API response', 'status': 500}
    return new_tokens


def decode_access_token(token: str):
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


@router.put('refresh/{id}', auth=None)
def refresh_nabat_session(request: HttpRequest, id: str):
    # TODO: check expiration time for nabat session object
    with transaction.atomic():
        try:
            session = NABatSession.objects.select_for_update().get(session_token=id)
        except NABatSession.DoesNotExist:
            return JsonResponse({'error': 'No NABat session found with the given ID'})
        auth_token = session.api_token
        refresh_token = session.refresh_token

        new_tokens = get_new_tokens(auth_token, refresh_token)
        if new_tokens['error']:
            return JsonResponse({'error': new_tokens['error']}, status=new_tokens.get('status', 500))
        session.refresh_token = new_tokens['refresh_token']
        session.api_token = new_tokens['access_token']
        session.save()
    token_data = decode_access_token(new_tokens['refresh_token'])
    token_expires = token_data['exp']

    return JsonResponse(
        data={
            'nabat_session_id': id,
            'expires_at': token_expires
        },
        status=200
    )


@router.post('create', auth=None)
def create_nabat_session(request: HttpRequest, tokens: RefreshSchema) -> str | JsonResponse:
    new_tokens = get_new_tokens(tokens.access_token, tokens.refresh_token)
    if new_tokens['error']:
        return JsonResponse({'error': new_tokens['error']}, status=new_tokens.get('status', 500))

    session = NABatSession(
        session_token=uuid4(),
        api_token=new_tokens['access_token'],
        refresh_token=new_tokens['refresh_token'],
        user_id=new_tokens['user_id']
    )
    session.save()

    token_data = decode_access_token(new_tokens['refresh_token'])
    token_expires = token_data['exp']

    return JsonResponse(
        data={
            'nabat_session_id': session.session_token,
            'expires_at': token_expires
        },
        status=200,
    )
