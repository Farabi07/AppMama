from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import  extend_schema, OpenApiParameter

from authentication.decorators import has_permissions
from authentication.models import Child
from authentication.serializers import *
from authentication.filters import ChildFilter

from commons.enums import PermissionEnum
from commons.pagination import Pagination

from authentication.permissions import IsAdmin
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


# Create your views here.
class ChildTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        try:
            # Now fetch Child by user relation, not email
            Child = Child.objects.get(user=self.user)
            serializer = ChildSerializer(Child)
            for k, v in serializer.data.items():
                data[k] = v
        except Child.DoesNotExist:
            # Optionally handle if user is not an Child
            pass
        return data
# @permission_classes([IsChild])
class ChildTokenObtainPairView(TokenObtainPairView):
    serializer_class = ChildTokenObtainPairSerializer
@extend_schema(
	parameters=[
		OpenApiParameter("page"),
		
		OpenApiParameter("size"),
  ],
	request=ChildListSerializer,
	responses=ChildListSerializer
)

@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Only authenticated users can access this view
def getAllChild(request):
    # Debugging: Ensure that the user is authenticated
    user = request.user  # This will be the authenticated user
    print(f"Authenticated User: {user}")
    
    # Debugging: Print the logged-in user's ID or other identifiers
    print(f"User ID: {user.id}")
    
    # Filter Childs for the specific user (assuming each Child is linked to a user via ForeignKey)
    Childs = Child.objects.filter(user=user)
    
    # Debugging: Print the number of Childs associated with the user
    print(f"Childs found for User {user.id}: {Childs.count()}")
    
    total_elements = Childs.count()

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
    Childs = pagination.paginate_data(Childs)

    # Debugging: Check the number of Childs after pagination
    print(f"Childs after pagination: {len(Childs)}")

    # Serialize the filtered Child data
    serializer = ChildListSerializer(Childs, many=True)

    # Prepare the response data
    response = {
        'Childs': serializer.data,
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
	request=ChildSerializer,
	responses=ChildSerializer
)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_LIST_VIEW.name])
def getAllChildWithoutPagination(request):
	Childs = Child.objects.all()

	serializer = ChildListSerializer(Childs, many=True)

	return Response({'Childs': serializer.data}, status=status.HTTP_200_OK)




@extend_schema(request=ChildSerializer, responses=ChildSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def getAChild(request, pk):
	try:
		Child = Child.objects.get(pk=pk)
		serializer = ChildSerializer(Child)
		return Response(serializer.data, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Child id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=ChildSerializer, responses=ChildSerializer)
@api_view(['GET'])
# @permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DETAILS_VIEW.name])
def searchChild(request):
	Childs = ChildFilter(request.GET, queryset=Child.objects.all())
	Childs = Childs.qs

	print('searched_products: ', Childs)

	total_elements = Childs.count()

	page = request.query_params.get('page')
	size = request.query_params.get('size')

	# Pagination
	pagination = Pagination()
	pagination.page = page
	pagination.size = size
	Childs = pagination.paginate_data(Childs)

	serializer = ChildListSerializer(Childs, many=True)

	response = {
		'Childs': serializer.data,
		'page': pagination.page,
		'size': pagination.size,
		'total_pages': pagination.total_pages,
		'total_elements': total_elements,
	}

	if len(Childs) > 0:
		return Response(response, status=status.HTTP_200_OK)
	else:
		return Response({'detail': f"There are no Childs matching your search"}, status=status.HTTP_400_BAD_REQUEST)








@extend_schema(request=ChildSerializer, responses=ChildSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Only authenticated users can create Childs
def createChild(request):
    data = request.data
    filtered_data = {}

    # Filter out empty or '0' values
    for key, value in data.items():
        if value != '' and value != '0':
            filtered_data[key] = value

    # Pass the request context to the serializer (this will give access to request.user)
    serializer = ChildSerializer(data=filtered_data, context={'request': request})

    if serializer.is_valid():
        # Now calling save() will pass the request context as expected
        serializer.save()  # This will use the create method of the serializer
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(request=ChildSerializer, responses=ChildSerializer)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_UPDATE.name, PermissionEnum.PERMISSION_PARTIAL_UPDATE.name])
def updateChild(request,pk):
	try:
		Child = Child.objects.get(pk=pk)
		data = request.data
		serializer = ChildSerializer(Child, data=data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_200_OK)
		else:
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
	except ObjectDoesNotExist:
		return Response({'detail': f"Child id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)




@extend_schema(request=ChildSerializer, responses=ChildSerializer)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
# @has_permissions([PermissionEnum.PERMISSION_DELETE.name])
def deleteChild(request, pk):
	try:
		Child = Child.objects.get(pk=pk)
		Child.delete()
		return Response({'detail': f'Child id - {pk} is deleted successfully'}, status=status.HTTP_200_OK)
	except ObjectDoesNotExist:
		return Response({'detail': f"Child id - {pk} doesn't exists"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def ChildImageUpload(request, pk):
    print("FILES:", request.FILES)
    print("DATA:", request.data)
    try:
        Child = Child.objects.get(pk=pk)
        # Use request.FILES for file uploads
        image = request.FILES.get('image')
        if image:
            Child.image = image
            Child.save()
            return Response(Child.image.url, status=status.HTTP_200_OK)
        else:
            response = {'detail': "Please upload a valid image"}
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
    except ObjectDoesNotExist:
        response = {'detail': f"User id - {pk} doesn't exists"}
        return Response(response, status=status.HTTP_400_BAD_REQUEST)
    
from rest_framework_simplejwt.tokens import RefreshToken

@api_view(['POST'])
def ChildLogin(request):
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response({"error": "Email and password are required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        Child = Child.objects.get(email=email)

        if not Child.password:
            return Response({"error": "No password set for this Child"}, status=status.HTTP_400_BAD_REQUEST)

        if not check_password(password, Child.password):
            return Response({"error": "Incorrect password"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Use the actual User instance
        if not Child.user:
            return Response({"error": "Child is not linked to a user"}, status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken.for_user(Child.user)  # ✅ Corrected
        access_token = str(refresh.access_token)

        return Response({
            'access': access_token,
            'refresh': str(refresh),
            'id': Child.id,
            'role': Child.role,
            'name': Child.name,
            'email': Child.email,
            'image': Child.image.url if Child.image else None,
        }, status=status.HTTP_200_OK)

    except Child.DoesNotExist:
        return Response({"error": "Child not found"}, status=status.HTTP_404_NOT_FOUND)



