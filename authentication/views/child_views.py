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


@permission_classes([IsAuthenticated])
@api_view(['PATCH'])
def ChildImageUpload(request, pk):
    print("FILES:", request.FILES)
    print("DATA:", request.data)
    
    try:
        child = Child.objects.get(pk=pk)
        
        # Get the uploaded image from request.FILES (if present)
        image = request.FILES.get('image')
        # Get the full name from request.data (if present)
        name = request.data.get('name')
        
        # Update image if provided
        if image:
            child.image = image
        # Update name if provided
        if name:
            child.name = name

        # If neither image nor name is provided, return an error
        if not image and not name:
            response = {'detail': "Please provide either an image or a name"}
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        # Save the child instance with the updated fields
        child.save()

        # Return the image URL and name as part of the response
        response_data = {
            'image_url': child.image.url if child.image else None,
            'name': child.name
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except ObjectDoesNotExist:
        response = {'detail': f"Child id - {pk} doesn't exist"}
        return Response(response, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        response = {'detail': f'An error occurred: {str(e)}'}
        return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
from rest_framework_simplejwt.tokens import RefreshToken

@api_view(['POST'])
def ChildLogin(request):
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response({"error": "Email and password are required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        child = Child.objects.get(email=email)

        if not child.password:
            return Response({"error": "No password set for this Child"}, status=status.HTTP_400_BAD_REQUEST)

        if not check_password(password, child.password):
            return Response({"error": "Incorrect password"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Use the actual User instance
        if not child.user:
            return Response({"error": "Child is not linked to a user"}, status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken.for_user(child.user)  # ✅ Corrected
        access_token = str(refresh.access_token)

        return Response({
            'access': access_token,
            'refresh': str(refresh),
            'id': child.id,
            'role': child.role,
            'name': child.name,
            'email': child.email,
            'image': child.image.url if child.image else None,
        }, status=status.HTTP_200_OK)

    except Child.DoesNotExist:
        return Response({"error": "Child not found"}, status=status.HTTP_404_NOT_FOUND)




@permission_classes([IsAuthenticated])
@extend_schema(request=PasswordChangeSerializer)
@api_view(['PATCH'])
def childPasswordChange(request, pk):
    try:
        # Retrieve the child by pk
        child = Child.objects.get(pk=pk)

        # Get the current password, new password, and confirm password from the request data
        data = request.data
        password = data.get('current_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        # Check if any of the fields are missing
        if not password or not new_password or not confirm_password:
            return Response({'detail': 'current_password, new_password, and confirm_password are required.'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Verify if the current password matches the child's existing password
        if not check_password(password, child.password):
            return Response({'detail': 'The current password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the new password matches the confirm password
        if new_password != confirm_password:
            return Response({'detail': 'The new password and confirm password do not match.'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Update the child's password
        child.password = make_password(new_password)
        child.save()

        return Response({'detail': f"Child Id - {pk}'s password has been changed successfully."},
                        status=status.HTTP_200_OK)
    
    except ObjectDoesNotExist:
        return Response({'detail': f"Child id - {pk} doesn't exist."}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({'detail': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
