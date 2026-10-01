import base64
import json
import logging

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from ninja.router import Router

logger = logging.getLogger(__name__)
router = Router()


def get_auth_header(request: HttpRequest):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    auth_header_parts = auth_header.split(" ")
    return auth_header_parts[1] if len(auth_header_parts) > 1 else None


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


def get_email_if_authorized(  # noqa: PLR0911
    request: HttpRequest,
    recording_id: int | None = None,
    recording_pk: int | None = None,
) -> str | JsonResponse:
    """
    Check API token validity with NABat API and return email from JWT if authorized.

    If the user is a superuser, short-circuit and return their email.
    Either `recording_id` or `recording_pk` must be provided.

    `recording_pk` refers to the primary key of a NABatRecording, from which the actual
    `recording_id` is retrieved.
    """
    # Superuser shortcut
    if request.user and request.user.is_authenticated and request.user.is_superuser:
        return request.user.email or "superuser@nabat.org"
    # Decode JWT token
    api_token = get_auth_header(request)
    try:
        payload = decode_jwt(api_token)
        email = payload.get("email")
        if not email:
            raise ValueError("Email not found in JWT payload")
    except Exception:
        logger.exception("Failed to decode JWT")
        return JsonResponse({"error": "Invalid API token"}, status=400)

    # Resolve recording_id from recording_pk if needed
    if recording_id is None:
        if recording_pk is None:
            return JsonResponse(
                {"error": "Either recording_id or recording_pk must be provided"}, status=400
            )

        nabat_recording = get_object_or_404(NABatRecording, pk=recording_pk)
        recording_id = nabat_recording.recording_id

    # Verify access with NABat API
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    query = QUERY % {"acoustic_file_id": recording_id}
    try:
        response = requests.post(
            settings.BATAI_NABAT_API_URL, json={"query": query}, headers=headers, timeout=30
        )
    except Exception:
        logger.exception("API request error")
        return JsonResponse({"error": "Failed to connect to NABat API"}, status=500)

    if response.status_code != 200:
        logger.error("NABat API rejected access: %s - %s", response.status_code, response.text)
        return JsonResponse(
            {"error": "Failed to verify access with NABat API"}, status=response.status_code
        )

    try:
        data = response.json()
        if data["data"]["presignedUrlFromAcousticFile"] is None:
            return JsonResponse({"error": "Recording not found or access denied"}, status=403)
    except (KeyError, TypeError, json.JSONDecodeError):
        logger.exception("Error decoding NABat API response")
        return JsonResponse({"error": "Malformed response from NABat API"}, status=500)

    return email
