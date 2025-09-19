from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import  extend_schema, OpenApiParameter

from authentication.decorators import has_permissions
from notification.models import Contact
from notification.serializers import ContactSerializer, ContactListSerializer
from notification.filters import ContactFilter

from commons.enums import PermissionEnum
from commons.pagination import Pagination




# Create your views here.

@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		
		OpenApiParameter("size"),
  ],
	request=ContactListSerializer,
	responses=ContactListSerializer
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def getAllContact(request):
    # Get the authenticated user
    user = request.user  # This will be the user from the authentication token
    
    # Filter contacts by the logged-in user (assuming a 'user' field in the Contact model)
    contacts = Contact.objects.filter(user=user)
    
    total_elements = contacts.count()

    # Get pagination parameters
    page = int(request.query_params.get('page', 1))  # Default page = 1
    size = int(request.query_params.get('size', 10))  # Default size = 10

    # Pagination
    pagination = Pagination()
    pagination.page = page
    pagination.size = size

    # Paginate the data
    contacts = pagination.paginate_data(contacts)

    # Serialize the paginated contacts
    serializer = ContactListSerializer(contacts, many=True)

    # Response data with pagination info
    response = {
        'contacts': serializer.data,  # Corrected spelling to 'contacts'
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
	request=ContactSerializer,
	responses=ContactSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllContactWithoutPagination(request):
	cities = Contact.objects.all()

	serializer = ContactListSerializer(cities, many=True)

	return Response({'cities': serializer.data}, status=status.HTTP_200_OK)




@extend_schema(request=ContactListSerializer, responses=ContactListSerializer)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def getAContact(request, pk):
	try:
		city = Contact.objects.get(pk=pk)
		serializer = ContactSerializer(city)
		return Response(serializer.data, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Contact id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=ContactListSerializer, responses=ContactListSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def searchContact(request):
	contacts = ContactFilter(request.GET, queryset=Contact.objects.all())
	contacts = contacts.qs

	print('searched_products: ', contacts)

	total_elements = contacts.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	contacts = pagination.paginate_data(contacts)

	serializer = ContactListSerializer(contacts, many=True)

	response = {
		'contacts': serializer.data,
		'page': pagination.page,
		'size': pagination.size,
		'total_pages': pagination.total_pages,
		'total_elements': total_elements,
	}

	if len(contacts) > 0:
		return Response(response, status=status.HTTP_200_OK)
	else:
		return Response({'detail': f"There are no contacts matching your search"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=ContactSerializer, responses=ContactSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_CREATE.name])
def createContact(request):
    data = request.data

    # Dynamically get all the fields from the Contact model
    filtered_data = {}
    model_fields = Contact._meta.get_fields()

    for field in model_fields:
        field_name = field.name
        if field_name in data:
            filtered_data[field_name] = data[field_name]
    
    # Add user to the data manually, if necessary
    filtered_data['user'] = request.user.id

    # Use the custom ContactSerializer
    serializer = ContactSerializer(data=filtered_data)

    if serializer.is_valid():
        contact = serializer.save()  # This will trigger the create method in the serializer
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





@extend_schema(request=ContactSerializer, responses=ContactSerializer)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_UPDATE.name, PermissionEnum.PERMISSION_PARTIAL_UPDATE.name])
def updateContact(request,pk):
	try:
		city = Contact.objects.get(pk=pk)
		data = request.data
		serializer = ContactSerializer(city, data=data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_200_OK)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	except ObjectDoesNotExist:
		return Response({'detail': f"Contact id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=ContactSerializer, responses=ContactSerializer)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DELETE.name])
def deleteContact(request, pk):
	try:
		city = Contact.objects.get(pk=pk)
		city.delete()
		return Response({'detail': f'Contact id - {pk} is deleted successfully'}, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Contact id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)

