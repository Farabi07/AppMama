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

# Create your views here.

@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		
		OpenApiParameter("size"),
  ],
	request=TaskListSerializer,
	responses=TaskListSerializer
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Ensures only authenticated users can access
def getAllTask(request):
    # Filter tasks created by the logged-in user (Farabi)
    tasks = Task.objects.filter(created_by=request.user)
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

@extend_schema( request={"type": "object", "properties": {"task_ids": {"type": "array", "items": {"type": "integer"}}, "recurrence": {"type":"object"}}}, responses={200: TaskListSerializer} ) 
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

    qs = Task.objects.filter(pk__in=task_ids, created_by=request.user)
    updated_count = 0
    for t in qs:
        t.is_recurring = True
        # store recurrence as JSON string in recurrence_pattern (model field is CharField)
        try:
            t.recurrence_pattern = json.dumps(recurrence)
        except Exception:
            t.recurrence_pattern = str(recurrence)
        t.save(update_fields=['is_recurring', 'recurrence_pattern', 'updated_at'])
        updated_count += 1

    serializer = TaskListSerializer(qs, many=True)
    return Response({"updated_count": updated_count, "tasks": serializer.data}, status=status.HTTP_200_OK)
