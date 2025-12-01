from urllib import response
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, OpenApiParameter

from authentication.decorators import has_permissions
from task.models import Task
from task.serializers import TaskSerializer, TaskListSerializer, TaskMinimalListSerializer
from task.filters import TaskFilter

from commons.enums import PermissionEnum
from commons.pagination import Pagination
from django.utils import timezone
import json
from datetime import timedelta, datetime as _datetime

# Import the helper function from task_helper.py
from task.task_helper import _generate_and_create_occurrences

try:
    from dateutil.relativedelta import relativedelta
except Exception:
    relativedelta = None


def _generate_future_dates(start_date, pattern, interval=1, count=1, until=None):
    dates = []
    current = start_date
    i = 0
    max_iter = 10000
    while len(dates) < count and i < max_iter:
        # Use a safe step: if client provided interval==0, advance by 1 to avoid infinite loops
        step = interval if (isinstance(interval, int) and interval > 0) else 1
        if pattern == 'daily':
            current = current + timedelta(days=step)
        elif pattern == 'weekly':
            current = current + timedelta(weeks=step)
        elif pattern == 'monthly':
            if relativedelta is None:
                # can't compute monthly without dateutil available
                return dates
            current = current + relativedelta(months=step)
        else:
            break

        if until and current > until:
            break

        dates.append(current)
        i += 1

    return dates


def _parse_recurrence(rp_raw):
    if not rp_raw:
        return None
    try:
        rp = json.loads(rp_raw)
    except Exception:
        return None
    pattern = (rp.get('pattern') or '').lower()
    try:
        # accept 0 as a valid interval value (means client requested 'no gap' semantics)
        interval = int(rp.get('interval', 0) or 0)
    except Exception:
        interval = 0
    until = rp.get('until')
    until_date = None
    if until:
        try:
            # accept YYYY-MM-DD or ISO datetime
            until_date = _datetime.fromisoformat(until).date()
        except Exception:
            try:
                until_date = _datetime.strptime(until, "%Y-%m-%d").date()
            except Exception:
                until_date = None
    return {"pattern": pattern, "interval": interval, "until": until_date}


@extend_schema(
    parameters=[
        OpenApiParameter("page"),
        OpenApiParameter("size"),
        OpenApiParameter("occurrences", type=int, description="Return N upcoming occurrences per task")
    ],
    request=TaskListSerializer,
    responses=TaskListSerializer
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getAllTask(request):
    tasks_qs = Task.objects.filter(created_by=request.user)
    total_elements = tasks_qs.count()

    page = request.query_params.get('page', 1)
    size = request.query_params.get('size', 10)
    occurrences_count = int(request.query_params.get('occurrences', 0) or 0)

    pagination = Pagination()
    pagination.page = page
    pagination.size = size
    paginated_tasks = pagination.paginate_data(tasks_qs)

    serializer = TaskListSerializer(paginated_tasks, many=True)
    serialized = serializer.data

    today = timezone.now().date()
    for idx, task_obj in enumerate(paginated_tasks):
        # default values
        serialized[idx]["next_occurrence"] = None
        if task_obj.recurrence_pattern and task_obj.is_recurring:
            rp = _parse_recurrence(task_obj.recurrence_pattern)
            if rp and rp.get("pattern"):
                # if scheduled_date itself is today or future, and within until => treat as next
                sd = task_obj.scheduled_date
                until = rp.get("until")
                if sd >= today and (not until or sd <= until):
                    serialized[idx]["next_occurrence"] = sd.isoformat()
                    start_for_generation = sd
                else:
                    start_for_generation = sd
                # generate next 1 (or N) occurrences after start_for_generation
                cnt = max(1, occurrences_count) if occurrences_count else 1
                future_dates = _generate_future_dates(start_for_generation, rp["pattern"], rp["interval"], count=cnt,
                                                      until=until)
                if future_dates:
                    serialized[idx]["next_occurrence"] = future_dates[0].isoformat()
                    if occurrences_count:
                        serialized[idx]["upcoming_occurrences"] = [d.isoformat() for d in future_dates]
                else:
                    serialized[idx]["next_occurrence"] = None
                    if occurrences_count:
                        serialized[idx]["upcoming_occurrences"] = []
        else:
            # not recurring
            serialized[idx]["recurrence"] = None

        # also expose parsed recurrence for UI convenience
        if task_obj.recurrence_pattern:
            try:
                serialized[idx]["recurrence"] = json.loads(task_obj.recurrence_pattern)
            except Exception:
                serialized[idx]["recurrence"] = task_obj.recurrence_pattern

    response = {
        'tasks': serialized,
        'page': pagination.page,
        'size': pagination.size,
        'total_pages': pagination.total_pages,
        'total_elements': total_elements,
    }

    return Response(response, status=status.HTTP_200_OK)


@extend_schema(
    parameters=[
        OpenApiParameter("page"),
        OpenApiParameter("size"),
    ],
    request=TaskSerializer,
    responses=TaskSerializer
)
@api_view(['GET'])
def getAllTaskWithoutPagination(request):
    tasks = Task.objects.all()
    serializer = TaskListSerializer(tasks, many=True)
    return Response({'tasks': serializer.data}, status=status.HTTP_200_OK)


@extend_schema(request=TaskSerializer, responses=TaskSerializer)
@api_view(['GET'])
def getATask(request, pk):
    try:
        tasks = Task.objects.get(pk=pk)
        serializer = TaskSerializer(tasks)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except ObjectDoesNotExist:
        return Response({'detail': f"Task id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(request=TaskSerializer, responses=TaskSerializer)
@api_view(['GET'])
def searchTask(request):
    tasks = TaskFilter(request.GET, queryset=Task.objects.all())
    tasks = tasks.qs

    print('searched_products: ', tasks)

    total_elements = tasks.count()

    page = request.query_params.get('page')
    size = request.query_params.get('size')

    # Pagination
    pagination = Pagination()
    pagination.page = page
    pagination.size = size
    tasks = pagination.paginate_data(tasks)

    serializer = TaskListSerializer(tasks, many=True)

    response = {
        'tasks': serializer.data,
        'page': pagination.page,
        'size': pagination.size,
        'total_pages': pagination.total_pages,
        'total_elements': total_elements,
    }

    if len(tasks) > 0:
        return Response(response, status=status.HTTP_200_OK)
    else:
        return Response({'detail': f"There are no tasks matching your search"}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(request=TaskSerializer, responses=TaskSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def createTask(request):
    data = request.data
    filtered_data = {}

    # Ensure the 'user' field is assigned the current user
    filtered_data['user'] = request.user  # Assign current user

    for key, value in data.items():
        if value != '' and value != '0':
            filtered_data[key] = value

    # Now create the task with the current user already set
    serializer = TaskSerializer(data=filtered_data)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(request=TaskSerializer, responses=TaskSerializer)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updateTask(request, pk):
    try:
        tasks = Task.objects.get(pk=pk)
        data = request.data
        serializer = TaskSerializer(tasks, data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except ObjectDoesNotExist:
        return Response({'detail': f"Task id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(request=TaskListSerializer, responses=TaskListSerializer)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def deleteTask(request, pk):
    try:
        tasks = Task.objects.get(pk=pk)
        tasks.delete()
        return Response({'detail': f'Task id - {pk} is deleted successfully'}, status=status.HTTP_200_OK)
    except ObjectDoesNotExist:
        return Response({'detail': f"Task id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    parameters=[
        OpenApiParameter("page"),
        OpenApiParameter("size"),
    ],
    request=TaskListSerializer,
    responses=TaskListSerializer
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getTodayTask(request):
    today = timezone.now().date()
    print("Today's date:", today)

    # Filter tasks by logged-in user
    tasks = Task.objects.filter(scheduled_date=today, created_by=request.user)

    total_elements = tasks.count()

    # Pagination
    page = request.query_params.get('page')
    size = request.query_params.get('size')

    pagination = Pagination()
    pagination.page = page
    pagination.size = size
    tasks = pagination.paginate_data(tasks)

    serializer = TaskListSerializer(tasks, many=True)

    response = {
        'tasks': serializer.data,
        'page': pagination.page,
        'size': pagination.size,
        'total_pages': pagination.total_pages,
        'total_elements': total_elements,
    }

    return Response(response, status=status.HTTP_200_OK)


@extend_schema(
    parameters=[
        OpenApiParameter("page"),
        OpenApiParameter("size"),
    ],
    request=TaskListSerializer,
    responses=TaskListSerializer
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getAllHealthTask(request):
    tasks = Task.objects.filter(created_by=request.user, task_category="health task")

    total_elements = tasks.count()

    # Retrieve pagination parameters from query parameters
    page = request.query_params.get('page', 1)  # Default to page 1 if not provided
    size = request.query_params.get('size', 10)  # Default to 10 tasks per page if not provided

    # Pagination logic
    pagination = Pagination()
    pagination.page = page
    pagination.size = size
    tasks = pagination.paginate_data(tasks)

    # Serialize the task data
    serializer = TaskListSerializer(tasks, many=True)

    # Prepare the response
    response = {
        'tasks': serializer.data,
        'page': pagination.page,
        'size': pagination.size,
        'total_pages': pagination.total_pages,
        'total_elements': total_elements,
    }

    return Response(response, status=status.HTTP_200_OK)


@extend_schema(
    request={
        "type": "object",
        "properties": {
            "task_ids": {
                "type": "array",
                "items": {"type": "integer"}
            },
            "recurrence": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "enum": ["daily", "weekly", "monthly"],
                        "description": "Repeat pattern"
                    },
                    "selected_dates": {
                        "type": "array",
                        "items": {"type": "string", "format": "date"},
                        "description": "Optional: User-selected specific dates for repetition (YYYY-MM-DD format). If provided, tasks will be created only on these dates."
                    }
                },
                "required": ["pattern"]
            }
        },
        "required": ["task_ids", "recurrence"]
    },
    responses={200: TaskListSerializer}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def setTasksRecurring(request):
    """
    Mark selected tasks as recurring and create repeated instances.
    
    Rules:
    - Daily: User can select any days from task date to end of month
    - Weekly: User can select any Sundays (if task is on Sunday) from task date to end of month
    - Monthly: User can select any 6th (if task is on 6th) from task month to end of year
    
    Example request body:
    
    Auto-generate dates:
    {
        "task_ids": [1, 2, 3],
        "recurrence": {
            "pattern": "daily"  // will auto-generate all days till end of month
        }
    }
    
    User selects specific dates:
    {
        "task_ids": [1],
        "recurrence": {
            "pattern": "daily",
            "selected_dates": ["2024-06-10", "2024-06-15", "2024-06-20", "2024-06-25"]
        }
    }
    """
    data = request.data or {}
    task_ids = data.get('task_ids') or []
    recurrence = data.get('recurrence') or {}

    # Validation
    if not isinstance(task_ids, list) or not task_ids:
        return Response(
            {"error": "task_ids must be a non-empty list"},
            status=status.HTTP_400_BAD_REQUEST
        )

    pattern = (recurrence.get('pattern') or '').lower()
    if not pattern or pattern not in ('daily', 'weekly', 'monthly'):
        return Response(
            {"error": "recurrence.pattern is required and must be one of: daily, weekly, monthly"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get tasks owned by current user
    qs = Task.objects.filter(pk__in=task_ids, created_by=request.user)

    if not qs.exists():
        return Response(
            {"error": "No tasks found with the provided IDs for this user"},
            status=status.HTTP_404_NOT_FOUND
        )

    updated_count = 0
    created_count = 0

    for task in qs:
        # Mark task as recurring
        task.is_recurring = True
        task.recurrence_pattern = recurrence
        task.save(update_fields=['is_recurring', 'recurrence_pattern', 'updated_at'])

        # Create repeated task occurrences using the imported helper function
        created_ids = _generate_and_create_occurrences(task, recurrence)
        created_count += len(created_ids)
        updated_count += 1

    serializer = TaskListSerializer(qs, many=True)

    return Response({
        "success": True,
        "message": f"Successfully set {updated_count} task(s) as recurring",
        "updated_count": updated_count,
        "created_occurrences": created_count,
        "tasks": serializer.data
    }, status=status.HTTP_200_OK)