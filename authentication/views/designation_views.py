from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import  extend_schema, OpenApiParameter

from authentication.decorators import has_permissions
from authentication.models import Designation
from authentication.serializers import DesignationSerializer, DesignationListSerializer
from authentication.filters import DesignationFilter

from commons.enums import PermissionEnum
from commons.pagination import Pagination




# Create your views here.

@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		OpenApiParameter("size"),
  ],
	request=DesignationSerializer,
	responses=DesignationSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllDesignation(request):
	designations = Designation.objects.all()
	total_elements = designations.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	designations = pagination.paginate_data(designations)

	serializer = DesignationListSerializer(designations, many=True)

	response = {
		'designations': serializer.data,
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
	request=DesignationSerializer,
	responses=DesignationSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllDesignationWithoutPagination(request):
	designations = Designation.objects.all()

	serializer = DesignationListSerializer(designations, many=True)

	response = {
		'designations': serializer.data,
	}

	return Response(response, status=status.HTTP_200_OK)




@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		OpenApiParameter("size"),
  ],
	request=DesignationSerializer,
	responses=DesignationSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllDesignationWithoutPagination(request):
	designations = Designation.objects.all()

	serializer = DesignationListSerializer(designations, many=True)

	return Response({'designations': serializer.data}, status=status.HTTP_200_OK)




@extend_schema(request=DesignationSerializer, responses=DesignationSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def getADesignation(request, pk):
	try:
		designation = Designation.objects.get(pk=pk)
		serializer = DesignationSerializer(designation)
		return Response(serializer.data, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Designation id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=DesignationSerializer, responses=DesignationSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def searchDesignation(request):
	designations = DesignationFilter(request.GET, queryset=Designation.objects.all())
	designations = designations.qs

	print('searched_products: ', designations)

	total_elements = designations.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	designations = pagination.paginate_data(designations)

	serializer = DesignationListSerializer(designations, many=True)

	response = {
		'designations': serializer.data,
		'page': pagination.page,
		'size': pagination.size,
		'total_pages': pagination.total_pages,
		'total_elements': total_elements,
	}

	if len(designations) > 0:
		return Response(response, status=status.HTTP_200_OK)
	else:
		return Response({'detail': f"There are no designations matching your search"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=DesignationSerializer, responses=DesignationSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_CREATE.name])
def createDesignation(request):
	data = request.data
	filtered_data = {}

	for key, value in data.items():
		if value != '' and value != '0':
			filtered_data[key] = value

	serializer = DesignationSerializer(data=filtered_data)

	if serializer.is_valid():
		serializer.save()
		return Response(serializer.data, status=status.HTTP_201_CREATED)
	else:
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=DesignationSerializer, responses=DesignationSerializer)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_UPDATE.name, PermissionEnum.PERMISSION_PARTIAL_UPDATE.name])
def updateDesignation(request,pk):
	try:
		designation = Designation.objects.get(pk=pk)
		data = request.data
		serializer = DesignationSerializer(designation, data=data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_200_OK)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	except ObjectDoesNotExist:
		return Response({'detail': f"Designation id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=DesignationSerializer, responses=DesignationSerializer)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DELETE.name])
def deleteDesignation(request, pk):
	try:
		designation = Designation.objects.get(pk=pk)
		designation.delete()
		return Response({'detail': f'Designation id - {pk} is deleted successfully'}, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Designation id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)

