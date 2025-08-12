from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import  extend_schema, OpenApiParameter

from authentication.decorators import has_permissions
from authentication.models import Partner
from authentication.serializers import *
from authentication.filters import PartnerFilter

from commons.enums import PermissionEnum
from commons.pagination import Pagination

from authentication.permissions import  IsAdmin
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


# Create your views here.
class PartnerTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        try:
            # Now fetch Partner by user relation, not email
            Partner = Partner.objects.get(user=self.user)
            serializer = PartnerSerializer(Partner)
            for k, v in serializer.data.items():
                data[k] = v
        except Partner.DoesNotExist:
            # Optionally handle if user is not an Partner
            pass
        return data
# @permission_classes([IsPartner])
class PartnerTokenObtainPairView(TokenObtainPairView):
    serializer_class = PartnerTokenObtainPairSerializer
@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		
		OpenApiParameter("size"),
  ],
	request=PartnerListSerializer,
	responses=PartnerListSerializer
)

@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Only authenticated users can access this view
def getAllPartner(request):
    # Debugging: Ensure that the user is authenticated
    user = request.user  # This will be the authenticated user
    print(f"Authenticated User: {user}")
    
    # Debugging: Print the logged-in user's ID or other identifiers
    print(f"User ID: {user.id}")
    
    # Filter Partners for the specific user (assuming each Partner is linked to a user via ForeignKey)
    Partners = Partner.objects.filter(user=user)
    
    # Debugging: Print the number of Partners associated with the user
    print(f"Partners found for User {user.id}: {Partners.count()}")
    
    total_elements = Partners.count()

    # Pagination: Ensure page and size are integers
    try:
        page = int(request.query_params.get('page', 1))  # Default to 1 if page is not provided
        size = int(request.query_params.get('size', 10))  # Default to 10 if size is not provided
    except ValueError:
        return Response(
            {"detail": "Page and size must be integers."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Debugging: Check the pagination values
    print(f"Pagination - Page: {page}, Size: {size}")

    # Pagination
    pagination = Pagination()
    pagination.page = page
    pagination.size = size

    # Apply pagination
    Partners = pagination.paginate_data(Partners)

    # Debugging: Check the number of Partners after pagination
    print(f"Partners after pagination: {len(Partners)}")

    # Serialize the filtered Partner data
    serializer = PartnerListSerializer(Partners, many=True)

    # Prepare the response data
    response = {
        'Partners': serializer.data,
        'page': pagination.page,
        'size': pagination.size,
        'total_pages': pagination.total_pages,
        'total_elements': total_elements,
    }

    # Debugging: Print the response before returning it
    print(f"Response data: {response}")

    return Response(response, status=status.HTTP_200_OK)



@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		OpenApiParameter("size"),
  ],
	request=PartnerSerializer,
	responses=PartnerSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllPartnerWithoutPagination(request):
	Partners = Partner.objects.all()

	serializer = PartnerListSerializer(Partners, many=True)

	return Response({'Partners': serializer.data}, status=status.HTTP_200_OK)




@extend_schema(request=PartnerSerializer, responses=PartnerSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def getAPartner(request, pk):
	try:
		Partner = Partner.objects.get(pk=pk)
		serializer = PartnerSerializer(Partner)
		return Response(serializer.data, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Partner id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=PartnerSerializer, responses=PartnerSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def searchPartner(request):
	Partners = PartnerFilter(request.GET, queryset=Partner.objects.all())
	Partners = Partners.qs

	print('searched_products: ', Partners)

	total_elements = Partners.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	Partners = pagination.paginate_data(Partners)

	serializer = PartnerListSerializer(Partners, many=True)

	response = {
		'Partners': serializer.data,
		'page': pagination.page,
		'size': pagination.size,
		'total_pages': pagination.total_pages,
		'total_elements': total_elements,
	}

	if len(Partners) > 0:
		return Response(response, status=status.HTTP_200_OK)
	else:
		return Response({'detail': f"There are no Partners matching your search"}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(request=PartnerSerializer, responses=PartnerSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Only authenticated users can create Partners
def createPartner(request):
    data = request.data
    filtered_data = {}

    # Filter out empty or '0' values
    for key, value in data.items():
        if value != '' and value != '0':
            filtered_data[key] = value

    # Pass the request context to the serializer (this will give access to request.user)
    serializer = PartnerSerializer(data=filtered_data, context={'request': request})

    if serializer.is_valid():
        # Now calling save() will pass the request context as expected
        serializer.save()  # This will use the create method of the serializer
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(request=PartnerSerializer, responses=PartnerSerializer)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_UPDATE.name, PermissionEnum.PERMISSION_PARTIAL_UPDATE.name])
def updatePartner(request,pk):
	try:
		Partner = Partner.objects.get(pk=pk)
		data = request.data
		serializer = PartnerSerializer(Partner, data=data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_200_OK)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	except ObjectDoesNotExist:
		return Response({'detail': f"Partner id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=PartnerSerializer, responses=PartnerSerializer)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DELETE.name])
def deletePartner(request, pk):
	try:
		Partner = Partner.objects.get(pk=pk)
		Partner.delete()
		return Response({'detail': f'Partner id - {pk} is deleted successfully'}, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Partner id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def PartnerImageUpload(request, pk):
    print("FILES:", request.FILES)
    print("DATA:", request.data)
    try:
        Partner = Partner.objects.get(pk=pk)
        # Use request.FILES for file uploads
        image = request.FILES.get('image')
        if image:
            Partner.image = image
            Partner.save()
            return Response(Partner.image.url, status=status.HTTP_200_OK)
        else:
            response = {'detail': "Please upload a valid image"}
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
    except ObjectDoesNotExist:
        response = {'detail': f"User id - {pk} doesn't exists"}
        return Response(response, status=status.HTTP_400_BAD_REQUEST)
    
from rest_framework_simplejwt.tokens import RefreshToken

@api_view(['POST'])
def PartnerLogin(request):
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response({"error": "Email and password are required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        Partner = Partner.objects.get(email=email)

        if not Partner.password:
            return Response({"error": "No password set for this Partner"}, status=status.HTTP_400_BAD_REQUEST)

        if not check_password(password, Partner.password):
            return Response({"error": "Incorrect password"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Use the actual User instance
        if not Partner.user:
            return Response({"error": "Partner is not linked to a user"}, status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken.for_user(Partner.user)  # ✅ Corrected
        access_token = str(refresh.access_token)

        return Response({
            'access': access_token,
            'refresh': str(refresh),
            'id': Partner.id,
            'role': Partner.role,
            'name': Partner.name,
            'email': Partner.email,
            'image': Partner.image.url if Partner.image else None,
        }, status=status.HTTP_200_OK)

    except Partner.DoesNotExist:
        return Response({"error": "Partner not found"}, status=status.HTTP_404_NOT_FOUND)



