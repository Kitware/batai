import logging
from uuid import uuid4

from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest
from ninja.router import Router

from bats_ai.core.models.nabat import NABatSession

logger = logging.getLogger(__name__)
router = Router()


@router.post('{survey_event_id}/fileId/{file_id}', auth=None, response={200: str})
def create_nabat_session(request: HttpRequest, survey_event_id: str, file_id: str):
    api_token = request.headers.get('api-token', None)
    refresh_token = request.headers.get('refresh_token', None)
    user_id = request.headers.get('user', None)

    if not api_token:
        logger.error('Missing API Token header. Unable to create an NABat session')
        return HttpResponseBadRequest()
    if not refresh_token:
        logger.error('Missing Refresh Token header. Unable to create an NABat session.')

    session = NABatSession(
        session_token=uuid4(),
        api_token=api_token,
        refresh_token=refresh_token,
        survey_event_id=survey_event_id,
        file_id=file_id,
        user_id=user_id,
    )
    session.save()
    return HttpResponse(content='Success')


@router.post('session/refresh', auth=None)
def refresh_nabat_session(request: HttpRequest):
    session_cookie = request.COOKIES.get('nabat_session_token', None)
    if not session_cookie:
        logger.error('Missing required cookie. Unable to refresh session.')
        return HttpResponseBadRequest()

    nabat_session = NABatSession.objects.get(session_token=session_cookie)
    if not nabat_session:
        logger.error('Couble not locate session.')
        return Http404()

    # 1. Make a request to the NABat server using the refresh token
    # 2. Check the response for any errors
    # 3. Update the session object with the new auth token
    # 4. Return a 200 for success
