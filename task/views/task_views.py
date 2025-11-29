from urllib import response
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import  extend_schema, OpenApiParameter

from authentication.decorators import has_permissions
from task.models import Task
from task.serializers import TaskSerializer, TaskListSerializer,TaskMinimalListSerializer
from task.filters import TaskFilter

from commons.enums import PermissionEnum
from commons.pagination import Pagination
from django.utils import timezone
import json 
from datetime import timedelta
from datetime import timedelta, datetime as _datetime
try:
    from dateutil.relativedelta import relativedelta
except Exception:
    relativedelta = None
# Create your views here.

@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		
		OpenApiParameter("size"),
  ],
	request=TaskListSerializer,
	responses=TaskListSerializer
)


# ...existing code...

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
                future_dates = _generate_future_dates(start_for_generation, rp["pattern"], rp["interval"], count=cnt, until=until)
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
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllTaskWithoutPagination(request):
	tasks = Task.objects.all()

	serializer = TaskListSerializer(tasks, many=True)

	return Response({'tasks': serializer.data}, status=status.HTTP_200_OK)




@extend_schema(request=TaskSerializer, responses=TaskSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def getATask(request, pk):
	try:
		tasks = Task.objects.get(pk=pk)
		serializer = TaskSerializer(tasks)
		return Response(serializer.data, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Task id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=TaskSerializer, responses=TaskSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
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
# @has_permissions([PermissionEnum.PERMISSION_CREATE.name])
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
# @has_permissions([PermissionEnum.PERMISSION_UPDATE.name, PermissionEnum.PERMISSION_PARTIAL_UPDATE.name])
def updateTask(request,pk):
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
# @has_permissions([PermissionEnum.PERMISSION_DELETE.name])
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
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getTodayTask(request):
    today = timezone.now().date()
    print("Today's date:", today)

    # ✅ filter tasks by logged-in user
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

@extend_schema( request={"type": "object", "properties": {"task_ids": {"type": "array", "items": {"type": "integer"}}, "recurrence": {"type":"object", "properties": {"pattern":{"type":"string"}, "interval":{"type":"integer"}, "until":{"type":"string","format":"date"}}}}}, responses={200: TaskListSerializer} ) 
@api_view(['POST'])
@permission_classes([IsAuthenticated]) 
def setTasksRecurring(request):
    """ Mark selected tasks as recurring. Body example: { "task_ids": [1,2,3], "recurrence": {"pattern":"daily"|"weekly"|"monthly", "interval":1} } Only tasks owned by request.user (created_by) will be updated. """
    data = request.data or {}
    task_ids = data.get('task_ids') or []
    recurrence = data.get('recurrence') or {}

    if not isinstance(task_ids, list) or not task_ids:
        return Response({"error": "task_ids must be a non-empty list"}, status=status.HTTP_400_BAD_REQUEST)

    pattern = (recurrence.get('pattern') or '').lower()
    if pattern and pattern not in ('daily', 'weekly', 'monthly'):
        return Response({"error": "recurrence.pattern must be one of: daily, weekly, monthly"}, status=status.HTTP_400_BAD_REQUEST)

    # validate interval
    try:
        # allow 0 to mean "no gap" if the client intends that semantics
        interval = int(recurrence.get('interval', 1) or 0)
    except Exception:
        interval = 0
    if interval < 0:
        return Response({"error": "recurrence.interval must be an integer >= 0"}, status=status.HTTP_400_BAD_REQUEST)
    recurrence['interval'] = interval

    # Optional 'until' end-date for recurrence. Accepts ISO date (YYYY-MM-DD) or ISO datetime.
    until = recurrence.get('until')
    if until:
        from datetime import datetime, date
        parsed_date = None
        # try parsing common ISO formats
        if isinstance(until, (date, datetime)):
            parsed_date = until if isinstance(until, date) else until.date()
        else:
            if not isinstance(until, str):
                return Response({"error": "recurrence.until must be a date string in YYYY-MM-DD or ISO format"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                # try full ISO datetime first
                parsed_dt = datetime.fromisoformat(until)
            except Exception:
                try:
                    parsed_dt = datetime.strptime(until, "%Y-%m-%d")
                except Exception:
                    return Response({"error": "recurrence.until must be a date string in YYYY-MM-DD or ISO format"}, status=status.HTTP_400_BAD_REQUEST)
            parsed_date = parsed_dt.date()
        # store normalized ISO date string
        recurrence['until'] = parsed_date.isoformat()

    qs = Task.objects.filter(pk__in=task_ids, created_by=request.user)
    updated_count = 0
    for t in qs:
        t.is_recurring = True
        # recurrence_pattern is a JSONField now — store dict directly
        t.recurrence_pattern = recurrence
        t.save(update_fields=['is_recurring', 'recurrence_pattern', 'updated_at'])
        updated_count += 1

    serializer = TaskListSerializer(qs, many=True)
    return Response({"updated_count": updated_count, "tasks": serializer.data}, status=status.HTTP_200_OK)
