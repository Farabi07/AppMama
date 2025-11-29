from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from task.models import Pantry
from task.serializers import PantryMinimalSerializer, PantrySerializer, PantryListSerializer
from task.filters import PantryFilter

from drf_spectacular.utils import  extend_schema, OpenApiParameter
from commons.pagination import Pagination




# Create your views here.

@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		OpenApiParameter("size"),
  ],
	request=PantryMinimalSerializer,
	responses=PantryMinimalSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllPantry(request):
    # Fetch all pantry items
    itemss = Pantry.objects.all()
    total_elements = itemss.count()

    # Get pagination parameters from query parameters
    page = request.query_params.get('page', 1)  # Default to page 1 if not provided
    size = request.query_params.get('size', 10)  # Default to size 10 if not provided

    # Pagination
    pagination = Pagination()
    pagination.page = int(page)  # Ensure page is an integer
    pagination.size = int(size)  # Ensure size is an integer
    itemss = pagination.paginate_data(itemss)

    # Serialize the data with only 'name' and 'quantity' fields
    serializer = PantryMinimalSerializer(itemss, many=True)

    # Prepare the response
    response = {
        'items': serializer.data,
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
	request=PantrySerializer,
	responses=PantrySerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllPantryWithoutPagination(request):
	itemss = Pantry.objects.all()

	serializer = PantryListSerializer(itemss, many=True)

	return Response({'itemss': serializer.data}, status=status.HTTP_200_OK)




@extend_schema(request=PantrySerializer, responses=PantrySerializer)
@api_view(['GET'])
def getAPantry(request, pk):
	try:
		items = Pantry.objects.get(pk=pk)
		serializer = PantrySerializer(items)
		return Response(serializer.data, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Pantry id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=PantrySerializer, responses=PantrySerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PRODUCT_DETAILS.name])
def searchPantry(request):

	items = PantryFilter(request.GET, queryset=Pantry.objects.all())
	items = items.qs

	print('items: ', items)

	total_elements = items.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	itemss = pagination.paginate_data(itemss)

	serializer = PantryListSerializer(itemss, many=True)

	response = {
		'itemss': serializer.data,
		'page': pagination.page,
		'size': pagination.size,
		'total_pages': pagination.total_pages,
		'total_elements': total_elements,
	}

	if len(itemss) > 0:
		return Response(response, status=status.HTTP_200_OK)
	else:
		return Response({'detail': f"There are no itemss matching your search"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=PantrySerializer, responses=PantrySerializer)
@api_view(['POST'])
def createPantry(request):
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
			items = Pantry.objects.get(name=name)
			return Response({'detail': f"Pantry with name '{name}' already exists."})
		except Pantry.DoesNotExist:
			pass

	serializer = PantrySerializer(data=filtered_data)

	if serializer.is_valid():
		serializer.save()
		return Response(serializer.data, status=status.HTTP_201_CREATED)
	else:
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=PantryMinimalSerializer, responses=PantryMinimalSerializer)
@api_view(['PUT'])
def updatePantry(request):
    """
    Allows users to update quantities of multiple pantry items based on their name.
    """
    data = request.data.get('items', [])

    if not data:
        return Response({"error": "No items provided to update."}, status=status.HTTP_400_BAD_REQUEST)

    updated_items = []

    for item_data in data:
        name = item_data.get("name")
        quantity = item_data.get("quantity")

        if not name or quantity is None:
            return Response({"error": "Each item must have 'name' and 'quantity'."}, status=status.HTTP_400_BAD_REQUEST)

        # Find all pantry items with the given name
        items = Pantry.objects.filter(name=name)

        if not items.exists():
            return Response({"error": f"No pantry items found with name '{name}'."}, status=status.HTTP_404_NOT_FOUND)

        # Update the quantity for each item
        for item in items:
            item.quantity = quantity
            item.save()
            updated_items.append(PantryMinimalSerializer(item).data)

    return Response(updated_items, status=status.HTTP_200_OK)



@extend_schema(request=PantrySerializer, responses=PantrySerializer)
@api_view(['DELETE'])
def deletePantry(request, pk):
	try:
		items = Pantry.objects.get(pk=pk)
		items.delete()
		return Response({'detail': f'Pantry id - {pk} is deleted successfully'}, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Pantry id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)

