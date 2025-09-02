from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import  extend_schema, OpenApiParameter

from authentication.decorators import has_permissions
from task.models import Receipt
from task.serializers import ReceiptSerializer, ReceiptListSerializer
from task.filters import ReceiptFilter

from commons.enums import PermissionEnum
from commons.pagination import Pagination




@extend_schema(
    parameters=[
        OpenApiParameter("page"),
        OpenApiParameter("size"),
    ],
    request=ReceiptSerializer,
    responses=ReceiptSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllReceipt(request):
    # Fetch all receipts
    recipts = Receipt.objects.all()
    total_elements = recipts.count()

    page = request.query_params.get('page')
    size = request.query_params.get('size')

    # Pagination
    pagination = Pagination()
    pagination.page = page
    pagination.size = size

    # Corrected variable name to 'recipts'
    recipts = pagination.paginate_data(recipts)

    # Serialize the paginated receipts
    serializer = ReceiptListSerializer(recipts, many=True)

    response = {
        'reciept': serializer.data,  # Notice the spelling here is correct as 'reciept'
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
	request=ReceiptSerializer,
	responses=ReceiptSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllReceiptWithoutPagination(request):
	reciept = Receipt.objects.all()

	serializer = ReceiptListSerializer(reciept, many=True)

	return Response({'reciept': serializer.data}, status=status.HTTP_200_OK)




@extend_schema(request=ReceiptSerializer, responses=ReceiptSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def getAReceipt(request, pk):
	try:
		city = Receipt.objects.get(pk=pk)
		serializer = ReceiptSerializer(city)
		return Response(serializer.data, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Receipt id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=ReceiptSerializer, responses=ReceiptSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def searchReceipt(request):
	reciept = ReceiptFilter(request.GET, queryset=Receipt.objects.all())
	reciept = reciept.qs

	print('searched_products: ', reciept)

	total_elements = reciept.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	reciept = pagination.paginate_data(reciept)

	serializer = ReceiptListSerializer(reciept, many=True)

	response = {
		'reciept': serializer.data,
		'page': pagination.page,
		'size': pagination.size,
		'total_pages': pagination.total_pages,
		'total_elements': total_elements,
	}

	if len(reciept) > 0:
		return Response(response, status=status.HTTP_200_OK)
	else:
		return Response({'detail': f"There are no reciept matching your search"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=ReceiptSerializer, responses=ReceiptSerializer)
@api_view(['POST'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_CREATE.name])
def createReceipt(request):
	data = request.data
	filtered_data = {}

	for key, value in data.items():
		if value != '' and value != '0':
			filtered_data[key] = value

	serializer = ReceiptSerializer(data=filtered_data)

	if serializer.is_valid():
		serializer.save()
		return Response(serializer.data, status=status.HTTP_201_CREATED)
	else:
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=ReceiptSerializer, responses=ReceiptSerializer)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_UPDATE.name, PermissionEnum.PERMISSION_PARTIAL_UPDATE.name])
def updateReceipt(request,pk):
	try:
		city = Receipt.objects.get(pk=pk)
		data = request.data
		serializer = ReceiptSerializer(city, data=data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_200_OK)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	except ObjectDoesNotExist:
		return Response({'detail': f"Receipt id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=ReceiptSerializer, responses=ReceiptSerializer)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DELETE.name])
def deleteReceipt(request, pk):
	try:
		client = Receipt.objects.get(pk=pk)
		client.delete()
		return Response({'detail': f'Receipt id - {pk} is deleted successfully'}, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Receipt id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)

