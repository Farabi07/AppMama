from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import  extend_schema, OpenApiParameter

from authentication.decorators import has_permissions
from task.models import PeptalkData
from task.serializers import PeptalkSerializer, PeptalkListSerializer
from task.filters import PeptalkFilter

from commons.enums import PermissionEnum
from commons.pagination import Pagination




# Create your views here.

@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		
		OpenApiParameter("size"),
  ],
	request=PeptalkSerializer,
	responses=PeptalkSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllPeptalk(request):
	cities = PeptalkData.objects.all()
	total_elements = cities.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	cities = pagination.paginate_data(cities)

	serializer = PeptalkListSerializer(cities, many=True)

	response = {
		'cities': serializer.data,
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
	request=PeptalkSerializer,
	responses=PeptalkSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllPeptalkWithoutPagination(request):
	cities = PeptalkData.objects.all()

	serializer = PeptalkListSerializer(cities, many=True)

	return Response({'cities': serializer.data}, status=status.HTTP_200_OK)




@extend_schema(request=PeptalkSerializer, responses=PeptalkSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def getAPeptalk(request, pk):
	try:
		city = PeptalkData.objects.get(pk=pk)
		serializer = PeptalkSerializer(city)
		return Response(serializer.data, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Peptalk id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=PeptalkSerializer, responses=PeptalkSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def searchPeptalk(request):
	cities = PeptalkFilter(request.GET, queryset=PeptalkData.objects.all())
	cities = cities.qs

	print('searched_products: ', cities)

	total_elements = cities.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	cities = pagination.paginate_data(cities)

	serializer = PeptalkListSerializer(cities, many=True)

	response = {
		'cities': serializer.data,
		'page': pagination.page,
		'size': pagination.size,
		'total_pages': pagination.total_pages,
		'total_elements': total_elements,
	}

	if len(cities) > 0:
		return Response(response, status=status.HTTP_200_OK)
	else:
		return Response({'detail': f"There are no cities matching your search"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=PeptalkSerializer, responses=PeptalkSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_CREATE.name])
def createPeptalk(request):
	data = request.data
	filtered_data = {}

	for key, value in data.items():
		if value != '' and value != '0':
			filtered_data[key] = value

	serializer = PeptalkSerializer(data=filtered_data)

	if serializer.is_valid():
		serializer.save()
		return Response(serializer.data, status=status.HTTP_201_CREATED)
	else:
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=PeptalkSerializer, responses=PeptalkSerializer)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_UPDATE.name, PermissionEnum.PERMISSION_PARTIAL_UPDATE.name])
def updatePeptalk(request,pk):
	try:
		city = PeptalkData.objects.get(pk=pk)
		data = request.data
		serializer = PeptalkSerializer(city, data=data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_200_OK)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	except ObjectDoesNotExist:
		return Response({'detail': f"Peptalk id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=PeptalkSerializer, responses=PeptalkSerializer)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DELETE.name])
def deletePeptalk(request, pk):
	try:
		city = PeptalkData.objects.get(pk=pk)
		city.delete()
		return Response({'detail': f'Peptalk id - {pk} is deleted successfully'}, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Peptalk id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)

