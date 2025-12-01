from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import  extend_schema, OpenApiParameter

from authentication.decorators import has_permissions
from task.models import Recipe
from task.serializers import RecipeSerializer, RecipeListSerializer
from task.filters import RecipeFilter

from commons.enums import PermissionEnum
from commons.pagination import Pagination




# Create your views here.
@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		
		OpenApiParameter("size"),
  ],
	request=RecipeSerializer,
	responses=RecipeSerializer
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllRecipe(request):
	recipes = Recipe.objects.filter(created_by=request.user).order_by('-created_at')
	total_elements = recipes.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	recipes = pagination.paginate_data(recipes)

	serializer = RecipeListSerializer(recipes, many=True)

	response = {
		'recipes': serializer.data,
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
	request=RecipeSerializer,
	responses=RecipeSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllRecipeWithoutPagination(request):
	recipes = Recipe.objects.all()

	serializer = RecipeListSerializer(recipes, many=True)

	return Response({'recipes': serializer.data}, status=status.HTTP_200_OK)




@extend_schema(request=RecipeSerializer, responses=RecipeSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def getARecipe(request, pk):
	try:
		city = Recipe.objects.get(pk=pk)
		serializer = RecipeSerializer(city)
		return Response(serializer.data, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Recipe id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=RecipeSerializer, responses=RecipeSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def searchRecipe(request):
	recipes = RecipeFilter(request.GET, queryset=Recipe.objects.all())
	recipes = recipes.qs

	print('searched_products: ', recipes)

	total_elements = recipes.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	recipes = pagination.paginate_data(recipes)

	serializer = RecipeListSerializer(recipes, many=True)

	response = {
		'recipes': serializer.data,
		'page': pagination.page,
		'size': pagination.size,
		'total_pages': pagination.total_pages,
		'total_elements': total_elements,
	}

	if len(recipes) > 0:
		return Response(response, status=status.HTTP_200_OK)
	else:
		return Response({'detail': f"There are no recipes matching your search"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=RecipeSerializer, responses=RecipeSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_CREATE.name])
def createRecipe(request):
	data = request.data
	filtered_data = {}

	for key, value in data.items():
		if value != '' and value != '0':
			filtered_data[key] = value

	serializer = RecipeSerializer(data=filtered_data)

	if serializer.is_valid():
		serializer.save()
		return Response(serializer.data, status=status.HTTP_201_CREATED)
	else:
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=RecipeSerializer, responses=RecipeSerializer)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_UPDATE.name, PermissionEnum.PERMISSION_PARTIAL_UPDATE.name])
def updateRecipe(request,pk):
	try:
		city = Recipe.objects.get(pk=pk)
		data = request.data
		serializer = RecipeSerializer(city, data=data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_200_OK)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	except ObjectDoesNotExist:
		return Response({'detail': f"Recipe id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=RecipeSerializer, responses=RecipeSerializer)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DELETE.name])
def deleteRecipe(request, pk):
	try:
		city = Recipe.objects.get(pk=pk)
		city.delete()
		return Response({'detail': f'Recipe id - {pk} is deleted successfully'}, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Recipe id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)

