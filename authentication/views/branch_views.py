from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import  extend_schema, OpenApiParameter

from authentication.decorators import has_permissions
from authentication.models import Branch, Employee
from authentication.serializers import BranchSerializer, BranchListSerializer
from authentication.filters import BranchFilter

from commons.enums import PermissionEnum
from commons.pagination import Pagination




# Create your views here.

@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		OpenApiParameter("size"),
  ],
	request=BranchSerializer,
	responses=BranchSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllBranch(request):
	branches = Branch.objects.all()
	total_elements = branches.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	branches = pagination.paginate_data(branches)

	serializer = BranchListSerializer(branches, many=True)

	response = {
		'branches': serializer.data,
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
	request=BranchSerializer,
	responses=BranchSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllBranchWithoutPagination(request):
	branches = Branch.objects.all()

	serializer = BranchListSerializer(branches, many=True)

	return Response({'branches': serializer.data}, status=status.HTTP_200_OK)




@extend_schema(request=BranchSerializer, responses=BranchSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def getABranch(request, pk):
	try:
		branch = Branch.objects.get(pk=pk)
		serializer = BranchSerializer(branch)
		return Response(serializer.data, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Branch id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=BranchSerializer, responses=BranchSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def getABranchByUserId(request, user_id):
	try:
		user_obj = Employee.objects.get(pk=user_id)
		if user_obj.branch:
			serializer = BranchSerializer(user_obj.branch)
			return Response(serializer.data, status=status.HTTP_200_OK)
		else:
			return Response({'detail': f"Employee id {user_id} has no branch."}, status=status.HTTP_400_BAD_REQUEST)
	except ObjectDoesNotExist:
		return Response({'detail': f"Employee id {user_id} doesn't exist"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=BranchSerializer, responses=BranchSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def searchBranch(request):
	branches = BranchFilter(request.GET, queryset=Branch.objects.all())
	branches = branches.qs

	print('searched_products: ', branches)

	total_elements = branches.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	branches = pagination.paginate_data(branches)

	serializer = BranchListSerializer(branches, many=True)

	response = {
		'branches': serializer.data,
		'page': pagination.page,
		'size': pagination.size,
		'total_pages': pagination.total_pages,
		'total_elements': total_elements,
	}

	if len(branches) > 0:
		return Response(response, status=status.HTTP_200_OK)
	else:
		return Response({'detail': f"There are no branches matching your search"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=BranchSerializer, responses=BranchSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_CREATE.name])
def createBranch(request):
	data = request.data
	filtered_data = {}

	for key, value in data.items():
		if value != '' and value != '0':
			filtered_data[key] = value

	serializer = BranchSerializer(data=filtered_data)

	if serializer.is_valid():
		serializer.save()
		return Response(serializer.data, status=status.HTTP_201_CREATED)
	else:
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=BranchSerializer, responses=BranchSerializer)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_UPDATE.name, PermissionEnum.PERMISSION_PARTIAL_UPDATE.name])
def updateBranch(request,pk):
	try:
		branch = Branch.objects.get(pk=pk)
		data = request.data
		serializer = BranchSerializer(branch, data=data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_200_OK)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	except ObjectDoesNotExist:
		return Response({'detail': f"Branch id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=BranchSerializer, responses=BranchSerializer)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DELETE.name])
def deleteBranch(request, pk):
	try:
		branch = Branch.objects.get(pk=pk)
		branch.delete()
		return Response({'detail': f'Branch id - {pk} is deleted successfully'}, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Branch id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)

