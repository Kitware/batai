import logging

from celery.result import AsyncResult
from django.db import transaction
from django.shortcuts import get_object_or_404
from ninja import Router

from bats_ai.core.models import ProcessingTask

logger = logging.getLogger(__name__)

# class ProcessingTaskSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ProcessingTask
#         fields = '__all__'


router = Router()

# @router.get("/filtered", response=List[ProcessingTaskSerializer])
# def filtered_tasks(request, status: Optional[str] = None):
#     if status and status not in ProcessingTask.Status.values:
#         return {"error": f"Invalid status value. Allowed values are {ProcessingTask.Status.values}."}, 400

#     tasks = ProcessingTask.objects.filter(status=status) if status else ProcessingTask.objects.all()
#     return ProcessingTaskSerializer(tasks, many=True).data


@router.get('/{task_id}/details')
def task_details(request, task_id: str):
    task = get_object_or_404(ProcessingTask, celery_id=task_id)
    celery_task = AsyncResult(task.celery_id)
    celery_data = {
        'state': celery_task.state,
        'status': task.status,
        'info': celery_task.info if not isinstance(celery_task.info, Exception) else None,
        'error': task.error
        or (str(celery_task.info) if isinstance(celery_task.info, Exception) else None),
    }
    return {'task': task.name, 'celery_data': celery_data}


@router.post('/{task_id}/cancel')
def cancel_task(request, task_id: str):
    task = get_object_or_404(ProcessingTask, pk=task_id)
    with transaction.atomic():
        task.delete()
        celery_task = AsyncResult(task.celery_id)
        if celery_task:
            celery_task.revoke(terminate=True)
        return {'message': 'Task successfully canceled.'}, 202
