from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import  extend_schema, OpenApiParameter

from authentication.decorators import has_permissions
from task.models import Client
from task.serializers import ClientSerializer, ClientListSerializer
from task.filters import ClientFilter

from commons.enums import PermissionEnum
from commons.pagination import Pagination




# Create your views here.

@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		
		OpenApiParameter("size"),
  ],
	request=ClientSerializer,
	responses=ClientSerializer
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllClient(request):
	clients = Client.objects.filter(user=request.user)
	total_elements = clients.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	clients = pagination.paginate_data(clients)

	serializer = ClientListSerializer(clients, many=True)

	response = {
		'clients': serializer.data,
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
	request=ClientSerializer,
	responses=ClientSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllClientWithoutPagination(request):
	clients = Client.objects.all()

	serializer = ClientListSerializer(clients, many=True)

	return Response({'clients': serializer.data}, status=status.HTTP_200_OK)




@extend_schema(request=ClientSerializer, responses=ClientSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def getAClient(request, pk):
	try:
		city = Client.objects.get(pk=pk)
		serializer = ClientSerializer(city)
		return Response(serializer.data, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Client id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=ClientSerializer, responses=ClientSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def searchClient(request):
	clients = ClientFilter(request.GET, queryset=Client.objects.all())
	clients = clients.qs

	print('searched_products: ', clients)

	total_elements = clients.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	clients = pagination.paginate_data(clients)

	serializer = ClientListSerializer(clients, many=True)

	response = {
		'clients': serializer.data,
		'page': pagination.page,
		'size': pagination.size,
		'total_pages': pagination.total_pages,
		'total_elements': total_elements,
	}

	if len(clients) > 0:
		return Response(response, status=status.HTTP_200_OK)
	else:
		return Response({'detail': f"There are no clients matching your search"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=ClientSerializer, responses=ClientSerializer)
@api_view(['POST'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_CREATE.name])
def createClient(request):
	data = request.data
	filtered_data = {}

	for key, value in data.items():
		if value != '' and value != '0':
			filtered_data[key] = value
	filtered_data['user'] = request.user 

	serializer = ClientSerializer(data=filtered_data)

	if serializer.is_valid():
		serializer.save()
		return Response(serializer.data, status=status.HTTP_201_CREATED)
	else:
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=ClientSerializer, responses=ClientSerializer)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_UPDATE.name, PermissionEnum.PERMISSION_PARTIAL_UPDATE.name])
def updateClient(request,pk):
	try:
		city = Client.objects.get(pk=pk)
		data = request.data
		serializer = ClientSerializer(city, data=data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_200_OK)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	except ObjectDoesNotExist:
		return Response({'detail': f"Client id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=ClientSerializer, responses=ClientSerializer)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DELETE.name])
def deleteClient(request, pk):
	try:
		client = Client.objects.get(pk=pk)
		client.delete()
		return Response({'detail': f'Client id - {pk} is deleted successfully'}, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Client id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)

