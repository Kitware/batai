import logging

from django.http import HttpRequest, JsonResponse
from ninja.pagination import Router

from bats_ai.core.models import ProcessingTask
from bats_ai.tasks.nabat.nabat_update_species import update_nabat_species

logger = logging.getLogger(__name__)

router = Router()


@router.post('/update-species')
def update_species_list(
    request: HttpRequest,
):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    existing_task = ProcessingTask.objects.filter(
        metadata__type='Updating Species',
        status__in=[ProcessingTask.Status.QUEUED, ProcessingTask.Status.RUNNING],
    ).first()

    if existing_task:
        return JsonResponse(
            {
                'error': 'A task is already updating the Species List.',
                'taskId': existing_task.celery_id,
                'status': existing_task.status,
            },
            status=409,
        )

    # use a task to start downloading the file using the API key and generate the spectrograms
    task = update_nabat_species.delay()
    ProcessingTask.objects.create(
        name='Updating Species List',
        status=ProcessingTask.Status.QUEUED,
        metadata={
            'type': 'Updating Species',
        },
        celery_id=task.id,
    )
    return {'taskId': task.id}
