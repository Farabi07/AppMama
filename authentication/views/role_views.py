from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from authentication.models import Role
from authentication.serializers import RoleSerializer, RoleListSerializer
from authentication.filters import RoleFilter

from drf_spectacular.utils import  extend_schema, OpenApiParameter
from commons.pagination import Pagination




# Create your views here.

@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		OpenApiParameter("size"),
  ],
	request=RoleSerializer,
	responses=RoleSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllRole(request):
	roles = Role.objects.all()
	total_elements = roles.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	roles = pagination.paginate_data(roles)

	serializer = RoleListSerializer(roles, many=True)

	response = {
		'roles': serializer.data,
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
	request=RoleSerializer,
	responses=RoleSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllRoleWithoutPagination(request):
	roles = Role.objects.all()

	serializer = RoleListSerializer(roles, many=True)

	return Response({'roles': serializer.data}, status=status.HTTP_200_OK)




@extend_schema(request=RoleSerializer, responses=RoleSerializer)
@api_view(['GET'])
def getARole(request, pk):
	try:
		role = Role.objects.get(pk=pk)
		serializer = RoleSerializer(role)
		return Response(serializer.data, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Role id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=RoleSerializer, responses=RoleSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PRODUCT_DETAILS.name])
def searchRole(request):

	roles = RoleFilter(request.GET, queryset=Role.objects.all())
	roles = roles.qs

	print('roles: ', roles)

	total_elements = roles.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	roles = pagination.paginate_data(roles)

	serializer = RoleListSerializer(roles, many=True)

	response = {
		'roles': serializer.data,
		'page': pagination.page,
		'size': pagination.size,
		'total_pages': pagination.total_pages,
		'total_elements': total_elements,
	}

	if len(roles) > 0:
		return Response(response, status=status.HTTP_200_OK)
	else:
		return Response({'detail': f"There are no roles matching your search"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=RoleSerializer, responses=RoleSerializer)
@api_view(['POST'])
def createRole(request):
	data = request.data
	print('data: ', data)

	filtered_data = {}

	for key, value in data.items():
		if value != '' and value != '0':
			filtered_data[key] = value

	name = filtered_data.get('name', None)
	if name is not None:
		try:
			name = str(name).upper()
			role = Role.objects.get(name=name)
			return Response({'detail': f"Role with name '{name}' already exists."})
		except Role.DoesNotExist:
			pass

	serializer = RoleSerializer(data=filtered_data)

	if serializer.is_valid():
		serializer.save()
		return Response(serializer.data, status=status.HTTP_201_CREATED)
	else:
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=RoleSerializer, responses=RoleSerializer)
@api_view(['PUT'])
def updateRole(request,pk):
	try:
		role = Role.objects.get(pk=pk)
		data = request.data
		serializer = RoleSerializer(role, data=data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_200_OK)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	except ObjectDoesNotExist:
		return Response({'detail': f"role id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=RoleSerializer, responses=RoleSerializer)
@api_view(['DELETE'])
def deleteRole(request, pk):
	try:
		role = Role.objects.get(pk=pk)
		role.delete()
		return Response({'detail': f'Role id - {pk} is deleted successfully'}, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Role id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)

